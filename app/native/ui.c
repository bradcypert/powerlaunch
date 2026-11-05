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
void pl_windows_prepare(void);
void pl_windows_style(void *window);
#endif
#include "icon_data.h"
#include "typography.h"
#define RAYGUI_IMPLEMENTATION
#include "../vendor/raygui.h"

#define FIELD_BYTES 16384
#define TEXTURES 24
/* One borrowed widget scratch buffer. Plum copies the result immediately;
 * records and editor state remain Plum values, not retained C buffers. */
static char field_buffer[FIELD_BYTES];
static float scale = 1;
static int activation_consumed;
static int requested_cursor = MOUSE_CURSOR_DEFAULT;
static int current_cursor = MOUSE_CURSOR_DEFAULT;
static int frame;
typedef struct { char *path; Texture2D image; unsigned int used; } Cover;
static Cover covers[TEXTURES];
static unsigned int clock_tick;
static Rectangle clip_stack[8];
static int clip_depth;
static Texture2D logo;
static int close_requested;
static int peak_textures;
static unsigned long long peak_texture_bytes;
static int input_enabled = 1;

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
#ifdef _WIN32
    pl_windows_prepare();
#endif
    SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_WINDOW_HIGHDPI);
    InitWindow(1280, 820, "Powerlaunch");
    if (!IsWindowReady()) {
        fprintf(stderr, "Powerlaunch could not open a graphics window. Check your display and OpenGL drivers.\n");
        exit(1);
    }
    SetWindowMinSize(920, 720);
    SetExitKey(KEY_NULL);
    SetTargetFPS(60);
#ifdef _WIN32
    SetLoadFileDataCallback(utf8_file_data);
    pl_windows_style(GetWindowHandle());
#endif
    Image icon = LoadImageFromMemory(".png", powerlaunch_icon, sizeof powerlaunch_icon);
    if (icon.data) {
        SetWindowIcon(icon);
        logo = LoadTextureFromImage(icon);
        SetTextureFilter(logo, TEXTURE_FILTER_BILINEAR);
        UnloadImage(icon);
    }
    GuiSetFont(pl_font_init());
    GuiSetStyle(DEFAULT, TEXT_SIZE, 17);
    GuiSetStyle(DEFAULT, TEXT_SPACING, 0);
    GuiSetStyle(DEFAULT, BACKGROUND_COLOR, 0x171A23ff);
    GuiSetStyle(DEFAULT, BORDER_COLOR_NORMAL, 0x414A60ff);
    GuiSetStyle(DEFAULT, BASE_COLOR_NORMAL, 0x1C202Bff);
    GuiSetStyle(DEFAULT, TEXT_COLOR_NORMAL, 0xEDF0F7ff);
    GuiSetStyle(DEFAULT, BORDER_COLOR_FOCUSED, 0xB9A7F2ff);
    GuiSetStyle(DEFAULT, BASE_COLOR_FOCUSED, 0x2F3048ff);
    GuiSetStyle(DEFAULT, TEXT_COLOR_FOCUSED, 0xFFFFFFFF);
    GuiSetStyle(DEFAULT, BORDER_COLOR_PRESSED, 0xB9A7F2ff);
    GuiSetStyle(DEFAULT, BASE_COLOR_PRESSED, 0x343044ff);
    GuiSetStyle(DEFAULT, TEXT_COLOR_PRESSED, 0xFFFFFFFF);
}
int pl_ui_done(void) {
    const char *limit = getenv("POWERLAUNCH_SMOKE_FRAMES");
    if (WindowShouldClose()) close_requested = 1;
    return limit && frame >= atoi(limit);
}
int pl_ui_close_requested(void) { int value = close_requested; close_requested = 0; return value; }
void pl_ui_begin(void) {
    scale = GetWindowScaleDPI().x;
    const char *override = getenv("POWERLAUNCH_UI_SCALE");
    if (override) scale = (float)atof(override);
    if (scale < 1) scale = 1;
    if (scale > 3) scale = 3;
    activation_consumed = 0;
    requested_cursor = MOUSE_CURSOR_DEFAULT;
    SetMouseScale(1 / scale, 1 / scale);
    BeginDrawing();
    ClearBackground(color(0x171A23));
    Camera2D camera = {0}; camera.zoom = scale;
    BeginMode2D(camera);
}
void pl_ui_end(void) {
    if (requested_cursor != current_cursor) {
        SetMouseCursor(requested_cursor);
        current_cursor = requested_cursor;
    }
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
        covers[i] = (Cover){0};
    }
    if (logo.id) UnloadTexture(logo);
    pl_font_close();
    CloseWindow();
    if (getenv("POWERLAUNCH_MEMORY_REPORT"))
        fprintf(stderr, "[powerlaunch-native] peak_textures=%d peak_texture_bytes=%llu textures_after_close=0\n",
            peak_textures, peak_texture_bytes);
}
long long pl_ui_width(void) { return (long long)(GetScreenWidth() / scale); }
long long pl_ui_height(void) { return (long long)(GetScreenHeight() / scale); }
void pl_ui_enable(int enabled) { input_enabled = enabled; if (enabled) GuiEnable(); else GuiDisable(); }
void pl_ui_consume_activation(void) { activation_consumed = 1; }
int pl_ui_key(long long key) {
    return input_enabled && !(activation_consumed && (key == KEY_ENTER || key == KEY_SPACE))
        && IsKeyPressed((int)key);
}
int pl_ui_down(long long key) { return input_enabled && IsKeyDown((int)key); }
long long pl_ui_wheel(void) {
    return input_enabled ? (long long)(GetMouseWheelMove() * 64) : 0;
}
int pl_ui_hover(long long x, long long y, long long w, long long h) {
    Vector2 mouse = GetMousePosition();
    return input_enabled && (!clip_depth || CheckCollisionPointRec(mouse, clip_stack[clip_depth - 1]))
        && CheckCollisionPointRec(mouse, box(x, y, w, h));
}
int pl_ui_interactive(long long x, long long y, long long w, long long h) {
    int over = pl_ui_hover(x, y, w, h);
    if (over) requested_cursor = MOUSE_CURSOR_POINTING_HAND;
    return over;
}
int pl_ui_released(void) { return input_enabled && IsMouseButtonReleased(MOUSE_BUTTON_LEFT); }
void pl_ui_round(long long x, long long y, long long w, long long h, long long hex) {
    DrawRectangleRounded(box(x, y, w, h), 0.16f, 8, color(hex));
}
long long pl_ui_measure(const char *text, long long size) {
    return (long long)pl_font_measure(text, (int)size);
}
void pl_ui_logo(long long x, long long y, long long size) {
    if (logo.id) DrawTexturePro(logo, (Rectangle){0, 0, 256, 256}, box(x, y, size, size), (Vector2){0,0}, 0, WHITE);
}
void pl_ui_rect(long long x, long long y, long long w, long long h, long long hex) {
    DrawRectangleRec(box(x, y, w, h), color(hex));
}
void pl_ui_text(const char *text, long long x, long long y, long long size, long long hex) {
    pl_font_draw(text, (float)x, (float)y, (int)size, color(hex));
}
int pl_ui_clicked(long long x, long long y, long long w, long long h) {
    Vector2 mouse = GetMousePosition();
    return input_enabled && IsMouseButtonPressed(MOUSE_BUTTON_LEFT)
        && (!clip_depth || CheckCollisionPointRec(mouse, clip_stack[clip_depth - 1]))
        && CheckCollisionPointRec(mouse, box(x, y, w, h));
}
void pl_ui_field(long long id, const char *text, long long x, long long y, long long w, long long h, int editing) {
    if (strlen(text) >= FIELD_BYTES) {
        GuiLabel(box(x, y, w, h), "Text exceeds prototype editor capacity");
        return;
    }
    if (pl_ui_hover(x, y, w, h)) requested_cursor = MOUSE_CURSOR_IBEAM;
    memcpy(field_buffer, text, strlen(text) + 1);
    GuiTextBox(box(x, y, w, h), field_buffer, FIELD_BYTES, editing);
    // This raygui version has no text-paste handler. Keep Ctrl+V local to the
    // active field; the cover paste shortcut is handled separately in Plum.
    if (input_enabled && editing && IsKeyPressed(KEY_V) &&
        (IsKeyDown(KEY_LEFT_CONTROL) || IsKeyDown(KEY_RIGHT_CONTROL))) {
        const char *paste = GetClipboardText();
        size_t length = strlen(field_buffer);
        size_t added = paste ? strlen(paste) : 0;
        if (added && added < FIELD_BYTES - length) {
            size_t cursor = textBoxCursorIndex < 0 ? 0 : (size_t)textBoxCursorIndex;
            if (cursor > length) cursor = length;
            memmove(field_buffer + cursor + added, field_buffer + cursor, length - cursor + 1);
            memcpy(field_buffer + cursor, paste, added);
            for (size_t i = cursor; i < cursor + added; i++)
                if (field_buffer[i] == '\r' || field_buffer[i] == '\n') field_buffer[i] = ' ';
            textBoxCursorIndex = (int)(cursor + added);
        }
    }
}
const char *pl_ui_value(long long id) { (void)id; return field_buffer; }
int pl_ui_image_valid(const char *path) {
    Image image = LoadImage(path);
    int valid = image.data != NULL;
    if (valid) UnloadImage(image);
    return valid;
}
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
int pl_ui_cover(const char *path, long long x, long long y, long long w, long long h) {
    if (!*path) return 0;
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
    if (!texture.id) return 0;
    int count = 0;
    unsigned long long bytes = 0;
    for (int i = 0; i < TEXTURES; i++) if (covers[i].image.id) {
        count++;
        bytes += (unsigned long long)covers[i].image.width * covers[i].image.height * 4;
    }
    if (count > peak_textures) peak_textures = count;
    if (bytes > peak_texture_bytes) peak_texture_bytes = bytes;
    float fit = (float)w / texture.width;
    if ((float)h / texture.height < fit) fit = (float)h / texture.height;
    Rectangle destination = {(float)x + ((float)w - texture.width * fit) / 2,
        (float)y + ((float)h - texture.height * fit) / 2, texture.width * fit, texture.height * fit};
    DrawTexturePro(texture, (Rectangle){0, 0, (float)texture.width, (float)texture.height}, destination, (Vector2){0, 0}, 0, WHITE);
    return 1;
}
