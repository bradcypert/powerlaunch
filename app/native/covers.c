/* UI-thread texture cache + CPU-only image adaptation. The worker, channels,
 * disk-cache policy and atomic file writes are owned by Plum. No native threads. */
#include "covers.h"
#include <raylib.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ENTRIES 256
#define MAX_TEXTURES 128
#define DEFAULT_BUDGET (64ULL * 1024 * 1024)
typedef enum { IDLE, QUEUED, LOADING, READY, FAILED } State;
typedef struct {
    char *path;
    Texture2D texture;
    unsigned long long used, requested, serial;
    int width, height;
    State state;
} Cover;
typedef struct { Image image; unsigned char *png; int png_size; } CoverImage;
static Cover covers[ENTRIES];
static unsigned long long frame, clock_tick, next_serial, in_flight;
static unsigned long long gpu_bytes, peak_gpu_bytes;
static int textures, peak_textures;
static atomic_ullong decodes, live_images;
static unsigned long long uploads, hits, misses, obsolete;
static int request_slot = -1;

static unsigned long long texture_bytes(Texture2D texture) {
    return (unsigned long long)texture.width * texture.height * 4;
}
static unsigned long long budget(void) {
    const char *value = getenv("POWERLAUNCH_TEXTURE_BUDGET_MB");
    int mb = value ? atoi(value) : 64;
    if (mb < 4 || mb > 64) return DEFAULT_BUDGET;
    return (unsigned long long)mb * 1024 * 1024;
}
static void release_texture(Cover *cover) {
    if (cover->texture.id) {
        gpu_bytes -= texture_bytes(cover->texture);
        textures--;
        UnloadTexture(cover->texture);
        cover->texture = (Texture2D){0};
    }
}
void pl_covers_begin(void) { frame++; }
static int find(const char *path) {
    for (int i = 0; i < ENTRIES; i++) if (covers[i].path && strcmp(covers[i].path, path) == 0) return i;
    return -1;
}
int pl_covers_draw(const char *path, long long x, long long y, long long w, long long h, float scale) {
    if (!*path) return 0;
    int slot = find(path);
    if (slot < 0) {
        slot = 0;
        for (int i = 0; i < ENTRIES; i++) {
            if (!covers[i].path) { slot = i; break; }
            if (covers[i].used < covers[slot].used) slot = i;
        }
        release_texture(&covers[slot]); free(covers[slot].path);
        covers[slot] = (Cover){.path = strdup(path)};
        if (!covers[slot].path) return 0;
    }
    Cover *cover = &covers[slot];
    cover->requested = frame; cover->used = ++clock_tick;
    int width = (int)(w * scale + 31) / 32 * 32;
    int height = (int)(h * scale + 31) / 32 * 32;
    if (width > 480) width = 480;
    if (height > 720) height = 720;
    if (width < 32) width = 32;
    if (height < 32) height = 32;
    if (cover->state == IDLE || (cover->state == READY && (width > cover->width || height > cover->height))) {
        cover->width = width; cover->height = height;
        cover->serial = ++next_serial; cover->state = QUEUED;
    }
    if (!cover->texture.id) { misses++; return 0; }
    hits++;
    Texture2D texture = cover->texture;
    float fit = (float)w / texture.width;
    if ((float)h / texture.height < fit) fit = (float)h / texture.height;
    Rectangle destination = {(float)x + ((float)w - texture.width * fit)/2,
        (float)y + ((float)h - texture.height * fit)/2, texture.width*fit, texture.height*fit};
    DrawTexturePro(texture, (Rectangle){0,0,(float)texture.width,(float)texture.height}, destination, (Vector2){0,0}, 0, WHITE);
    return 1;
}
int pl_cover_pending(const char *path) {
    int slot = find(path);
    return slot >= 0 && covers[slot].state != FAILED;
}
/* Borrowed path is copied immediately by Plum, before another draw/queue call. */
const char *pl_cover_next(void) {
    request_slot = -1;
    if (in_flight) return "";
    for (int i = 0; i < ENTRIES; i++) {
        if (covers[i].state != QUEUED || covers[i].requested + 1 < frame) continue;
        if (request_slot < 0 || covers[i].used > covers[request_slot].used) request_slot = i;
    }
    if (request_slot < 0) return "";
    Cover *cover = &covers[request_slot];
    in_flight = cover->serial; cover->state = LOADING;
    return cover->path;
}
long long pl_cover_in_flight_id(void) { return (long long)in_flight; }
long long pl_cover_request_width(void) { return request_slot < 0 ? 0 : covers[request_slot].width; }
long long pl_cover_request_height(void) { return request_slot < 0 ? 0 : covers[request_slot].height; }

/* Only the Plum worker calls these CPU operations; never touch GPU state here. */
long long pl_cover_decode(const char *path) {
    atomic_fetch_add(&decodes, 1);
    Image image = LoadImage(path);
    if (!image.data) return 0;
    if (image.width <= 0 || image.height <= 0 || (uint64_t)image.width * image.height > 16777216) {
        UnloadImage(image); return 0;
    }
    ImageFormat(&image, PIXELFORMAT_UNCOMPRESSED_R8G8B8A8);
    float ratio = (float)image.width / 480;
    if ((float)image.height / 720 > ratio) ratio = (float)image.height / 720;
    if (ratio > 1) {
        int width = (int)(image.width/ratio), height = (int)(image.height/ratio);
        ImageResize(&image, width > 0 ? width : 1, height > 0 ? height : 1);
    }
    CoverImage *result = calloc(1, sizeof *result);
    if (!result) { UnloadImage(image); return 0; }
    result->image = image;
    atomic_fetch_add(&live_images, 1);
    return (long long)(intptr_t)result;
}
void pl_cover_image_free(long long raw) {
    CoverImage *image = (CoverImage *)(intptr_t)raw;
    if (!image) return;
    UnloadImage(image->image);
    if (image->png) MemFree(image->png);
    free(image);
    atomic_fetch_sub(&live_images, 1);
}
long long pl_cover_encode(long long raw) {
    CoverImage *image = (CoverImage *)(intptr_t)raw;
    if (!image->png) image->png = ExportImageToMemory(image->image, ".png", &image->png_size);
    return image->png ? image->png_size : 0;
}
const char *pl_cover_encoded_data(long long raw) { return (const char *)((CoverImage *)(intptr_t)raw)->png; }
void pl_cover_resize(long long raw, long long width, long long height) {
    CoverImage *image = (CoverImage *)(intptr_t)raw;
    float ratio = (float)image->image.width / width;
    if ((float)image->image.height / height > ratio) ratio = (float)image->image.height / height;
    if (ratio > 1) {
        int w = (int)(image->image.width/ratio), h = (int)(image->image.height/ratio);
        ImageResize(&image->image, w > 0 ? w : 1, h > 0 ? h : 1);
    }
}
/* Main graphics thread only, before issuing this frame's draw calls. */
void pl_cover_accept(long long serial, long long raw) {
    if ((unsigned long long)serial != in_flight) return;
    in_flight = 0;
    Cover *cover = NULL;
    for (int i = 0; i < ENTRIES; i++) if (covers[i].serial == (unsigned long long)serial) { cover = &covers[i]; break; }
    if (!cover || cover->requested + 1 < frame) { if (cover) cover->state = IDLE; obsolete++; return; }
    if (!raw) { cover->state = FAILED; return; }
    CoverImage *image = (CoverImage *)(intptr_t)raw;
    unsigned long long bytes = (unsigned long long)image->image.width * image->image.height * 4;
    release_texture(cover);
    while (gpu_bytes + bytes > budget() || textures >= MAX_TEXTURES) {
        int victim = -1;
        for (int i = 0; i < ENTRIES; i++) if (&covers[i] != cover && covers[i].texture.id &&
            (victim < 0 || covers[i].used < covers[victim].used)) victim = i;
        if (victim < 0) break;
        release_texture(&covers[victim]); covers[victim].state = IDLE;
    }
    cover->texture = LoadTextureFromImage(image->image);
    cover->state = cover->texture.id ? READY : FAILED;
    if (cover->texture.id) {
        SetTextureFilter(cover->texture, TEXTURE_FILTER_BILINEAR);
        gpu_bytes += bytes; textures++; uploads++;
        if (gpu_bytes > peak_gpu_bytes) peak_gpu_bytes = gpu_bytes;
        if (textures > peak_textures) peak_textures = textures;
    }
}
void pl_covers_close(void) {
    for (int i = 0; i < ENTRIES; i++) {
        release_texture(&covers[i]); free(covers[i].path); covers[i] = (Cover){0};
    }
    if (getenv("POWERLAUNCH_MEMORY_REPORT")) {
        fprintf(stderr,"[powerlaunch-native] peak_textures=%d peak_texture_bytes=%llu textures_after_close=%d\n",peak_textures,peak_gpu_bytes,textures);
        fprintf(stderr,"[powerlaunch-covers] decodes=%llu uploads=%llu hits=%llu misses=%llu obsolete=%llu images_after_close=%llu budget_bytes=%llu\n",
            atomic_load(&decodes), uploads, hits, misses, obsolete, atomic_load(&live_images), budget());
    }
}
