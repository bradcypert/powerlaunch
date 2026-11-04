/* ABI adaptation only: window/input, widgets, and bounded texture resources.
 * The Plum application owns records, layout, focus, navigation, and actions. */
#include <raylib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOGDI
#define NOUSER
#include <windows.h>
#include <limits.h>
#endif
#define RAYGUI_IMPLEMENTATION
#include "../vendor/raygui.h"

#define FIELDS 16
#define FIELD_BYTES 16384
#define TEXTURES 24
static char fields[FIELDS][FIELD_BYTES];
static float scale = 1;
static Font font;
static int custom_font;
static int frame;
typedef struct { char *path; Texture2D image; unsigned int used; } Cover;
static Cover covers[TEXTURES];
static unsigned int clock_tick;
static Rectangle clip_stack[8];
static int clip_depth;

#ifdef _WIN32
/* raylib's default fopen path need not be UTF-8 on Windows. Keep cover and
 * font filenames in UTF-8 at the Plum boundary and use wide filesystem APIs. */
static unsigned char *utf8_file_data(const char *filename, int *size) {
    *size = 0;
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, filename, -1, NULL, 0);
    if (!count) return NULL;
    wchar_t *path = calloc((size_t)count, sizeof *path);
    if (!path) return NULL;
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, filename, -1, path, count);
    FILE *file = _wfopen(path, L"rb");
    free(path);
    if (!file) return NULL;
    if (_fseeki64(file, 0, SEEK_END) != 0) { fclose(file); return NULL; }
    long long length = _ftelli64(file);
    if (length <= 0 || length > 64 * 1024 * 1024 || _fseeki64(file, 0, SEEK_SET) != 0) {
        fclose(file); return NULL;
    }
    unsigned char *data = MemAlloc((unsigned int)length);
    if (!data) { fclose(file); return NULL; }
    size_t read = fread(data, 1, (size_t)length, file);
    int closed = fclose(file);
    if (read != (size_t)length || closed) { MemFree(data); return NULL; }
    *size = (int)length;
    return data;
}
#endif

static Color color(long long hex) {
    return (Color){(hex >> 16) & 255, (hex >> 8) & 255, hex & 255, 255};
}
static Rectangle box(long long x, long long y, long long w, long long h) {
    return (Rectangle){(float)x, (float)y, (float)w, (float)h};
}
void pl_ui_init(void) {
    SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_WINDOW_HIGHDPI);
    InitWindow(1280, 820, "Powerlaunch");
    if (!IsWindowReady()) {
        fprintf(stderr, "Powerlaunch could not open a graphics window. Check your display and OpenGL drivers.\n");
        exit(1);
    }
    SetWindowMinSize(1060, 780);
    SetExitKey(KEY_NULL);
    SetTargetFPS(60);
#ifdef _WIN32
    SetLoadFileDataCallback(utf8_file_data);
#endif
#ifdef _WIN32
    const char *face = "C:/Windows/Fonts/segoeui.ttf";
#elif defined(__APPLE__)
    const char *face = "/System/Library/Fonts/Supplemental/Arial.ttf";
#else
    const char *face = "/usr/share/fonts/TTF/OpenSans-Regular.ttf";
    if (!FileExists(face)) face = "/usr/share/fonts/TTF/DejaVuSans.ttf";
    if (!FileExists(face)) face = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf";
#endif
    if (FileExists(face)) {
        int codepoints[480];
        for (int i = 0; i < 480; i++) codepoints[i] = 32 + i;
        font = LoadFontEx(face, 40, codepoints, 480);
        custom_font = font.texture.id != 0;
        if (custom_font) { SetTextureFilter(font.texture, TEXTURE_FILTER_BILINEAR); GuiSetFont(font); }
    }
    GuiSetStyle(DEFAULT, TEXT_SIZE, 18);
    GuiSetStyle(DEFAULT, TEXT_SPACING, 0);
    GuiSetStyle(DEFAULT, BACKGROUND_COLOR, 0x181C24ff);
    GuiSetStyle(DEFAULT, BORDER_COLOR_NORMAL, 0x3C495Dff);
    GuiSetStyle(DEFAULT, BASE_COLOR_NORMAL, 0x232A36ff);
    GuiSetStyle(DEFAULT, TEXT_COLOR_NORMAL, 0xEEF0F4ff);
    GuiSetStyle(DEFAULT, BORDER_COLOR_FOCUSED, 0x819BCBff);
    GuiSetStyle(DEFAULT, BASE_COLOR_FOCUSED, 0x334563ff);
    GuiSetStyle(DEFAULT, TEXT_COLOR_FOCUSED, 0xFFFFFFFF);
    GuiSetStyle(DEFAULT, BORDER_COLOR_PRESSED, 0x819BCBff);
    GuiSetStyle(DEFAULT, BASE_COLOR_PRESSED, 0x415B86ff);
    GuiSetStyle(DEFAULT, TEXT_COLOR_PRESSED, 0xFFFFFFFF);
}
int pl_ui_done(void) {
    const char *limit = getenv("POWERLAUNCH_SMOKE_FRAMES");
    return WindowShouldClose() || (limit && frame >= atoi(limit));
}
void pl_ui_begin(void) {
    scale = GetWindowScaleDPI().x;
    const char *override = getenv("POWERLAUNCH_UI_SCALE");
    if (override) scale = (float)atof(override);
    if (scale < 1) scale = 1;
    if (scale > 3) scale = 3;
    SetMouseScale(1 / scale, 1 / scale);
    BeginDrawing();
    ClearBackground(color(0x181C24));
    Camera2D camera = {0}; camera.zoom = scale;
    BeginMode2D(camera);
}
void pl_ui_end(void) {
    EndMode2D();
    EndDrawing();
    frame++;
    const char *limit = getenv("POWERLAUNCH_SMOKE_FRAMES");
    const char *path = getenv("POWERLAUNCH_SCREENSHOT");
    if (limit && path && frame == atoi(limit)) TakeScreenshot(path);
}
void pl_ui_close(void) {
    for (int i = 0; i < TEXTURES; i++) {
        if (covers[i].image.id) UnloadTexture(covers[i].image);
        free(covers[i].path);
    }
    if (custom_font) UnloadFont(font);
    CloseWindow();
}
long long pl_ui_width(void) { return (long long)(GetScreenWidth() / scale); }
long long pl_ui_height(void) { return (long long)(GetScreenHeight() / scale); }
int pl_ui_key(long long key) { return IsKeyPressed((int)key); }
int pl_ui_down(long long key) { return IsKeyDown((int)key); }
long long pl_ui_wheel(void) {
    Vector2 mouse = GetMousePosition();
    return mouse.x >= 168 && mouse.x < GetScreenWidth() / scale - 400
        ? (long long)(GetMouseWheelMove() * 64) : 0;
}
void pl_ui_rect(long long x, long long y, long long w, long long h, long long hex) {
    DrawRectangleRec(box(x, y, w, h), color(hex));
}
void pl_ui_text(const char *text, long long x, long long y, long long size, long long hex) {
    DrawTextEx(GuiGetFont(), text, (Vector2){(float)x, (float)y}, (float)size, 0, color(hex));
}
int pl_ui_button(const char *text, long long x, long long y, long long w, long long h) {
    return GuiButton(box(x, y, w, h), text);
}
int pl_ui_clicked(long long x, long long y, long long w, long long h) {
    Vector2 mouse = GetMousePosition();
    return IsMouseButtonPressed(MOUSE_BUTTON_LEFT)
        && (!clip_depth || CheckCollisionPointRec(mouse, clip_stack[clip_depth - 1]))
        && CheckCollisionPointRec(mouse, box(x, y, w, h));
}
void pl_ui_field(long long id, const char *text, long long x, long long y, long long w, long long h, int editing) {
    if (id < 0 || id >= FIELDS) return;
    if (strlen(text) >= FIELD_BYTES) {
        GuiLabel(box(x, y, w, h), "Text exceeds prototype editor capacity");
        return;
    }
    memcpy(fields[id], text, strlen(text) + 1);
    GuiTextBox(box(x, y, w, h), fields[id], FIELD_BYTES, editing);
}
const char *pl_ui_value(long long id) { return id >= 0 && id < FIELDS ? fields[id] : ""; }
void pl_ui_clip(long long x, long long y, long long w, long long h) {
    Rectangle next = box(x, y, w, h);
    if (clip_depth) next = GetCollisionRec(next, clip_stack[clip_depth - 1]);
    if (clip_depth < 8) clip_stack[clip_depth++] = next;
    BeginScissorMode((int)(next.x * scale), (int)(next.y * scale),
        (int)(next.width * scale), (int)(next.height * scale));
}
void pl_ui_unclip(void) {
    if (clip_depth) clip_depth--;
    if (!clip_depth) EndScissorMode();
    else {
        Rectangle r = clip_stack[clip_depth - 1];
        BeginScissorMode((int)(r.x * scale), (int)(r.y * scale), (int)(r.width * scale), (int)(r.height * scale));
    }
}
void pl_ui_cover(const char *path, long long x, long long y, long long w, long long h) {
    if (!*path) return;
    clock_tick++;
    int slot = -1;
    for (int i = 0; i < TEXTURES; i++) {
        if (covers[i].path && strcmp(covers[i].path, path) == 0) { slot = i; break; }
    }
    if (slot < 0) {
        slot = 0;
        for (int i = 0; i < TEXTURES; i++) {
            if (!covers[i].path) { slot = i; break; }
            if (covers[i].used < covers[slot].used) slot = i;
        }
        free(covers[slot].path);
        if (covers[slot].image.id) UnloadTexture(covers[slot].image);
        covers[slot].image = (Texture2D){0};
        covers[slot].path = strdup(path);
        Image image = LoadImage(path);
        if (image.data) {
            float shrink = (float)image.width / 480;
            if ((float)image.height / 720 > shrink) shrink = (float)image.height / 720;
            if (shrink > 1) ImageResize(&image, (int)(image.width / shrink), (int)(image.height / shrink));
            covers[slot].image = LoadTextureFromImage(image);
            UnloadImage(image);
            SetTextureFilter(covers[slot].image, TEXTURE_FILTER_BILINEAR);
        }
    }
    covers[slot].used = clock_tick;
    Texture2D texture = covers[slot].image;
    if (!texture.id) return;
    float fit = (float)w / texture.width;
    if ((float)h / texture.height < fit) fit = (float)h / texture.height;
    Rectangle destination = {(float)x + ((float)w - texture.width * fit) / 2,
        (float)y + ((float)h - texture.height * fit) / 2, texture.width * fit, texture.height * fit};
    DrawTexturePro(texture, (Rectangle){0, 0, (float)texture.width, (float)texture.height}, destination, (Vector2){0, 0}, 0, WHITE);
}
