/* Clipboard/raylib ABI adaptation only. Plum owns draft and persistence policy. */
#include <raylib.h>
#include <stdint.h>
#include <stdlib.h>

typedef struct { unsigned char *png; int size; } ClipboardImage;
static const char *last_error;

long long pl_clipboard_capture(void) {
    last_error = "The clipboard has no supported image. Copy an image, then try Paste cover.";
#if defined(__APPLE__)
    /* The selected raylib desktop backend does not implement image paste here. */
    last_error = "Image paste is not available on macOS yet. Use Choose cover.";
    return 0;
#else
    Image image = GetClipboardImage();
    if (!image.data) return 0;
    if (image.width <= 0 || image.height <= 0 ||
        (uint64_t)image.width * (uint64_t)image.height > 16777216) {
        UnloadImage(image);
        last_error = "That image is too large. Choose an image with at most 16 megapixels.";
        return 0;
    }
    int size = 0;
    unsigned char *png = ExportImageToMemory(image, ".png", &size);
    UnloadImage(image);
    if (!png || size <= 0 || size > 64 * 1024 * 1024) {
        if (png) MemFree(png);
        last_error = "The clipboard image could not be converted to a cover PNG.";
        return 0;
    }
    ClipboardImage *capture = malloc(sizeof *capture);
    if (!capture) { MemFree(png); last_error = "Not enough memory to paste this cover."; return 0; }
    *capture = (ClipboardImage){png, size};
    return (long long)(intptr_t)capture;
#endif
}
const char *pl_clipboard_error(void) { return last_error; }
long long pl_clipboard_size(long long raw) { return ((ClipboardImage *)(intptr_t)raw)->size; }
const char *pl_clipboard_data(long long raw) { return (const char *)((ClipboardImage *)(intptr_t)raw)->png; }
void pl_clipboard_free(long long raw) {
    ClipboardImage *capture = (ClipboardImage *)(intptr_t)raw;
    if (capture) { MemFree(capture->png); free(capture); }
}
