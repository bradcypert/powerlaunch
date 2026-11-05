/* Owns font selection, atlas lifetime, drawing and matching measurement.
 * Preserve the current rasterization for this refactor. Native-size/DPI font
 * comparisons can now change this policy without touching window or widgets. */
#include "typography.h"
static Font font;
static int custom_font;
Font pl_font_init(void) {
    font = GetFontDefault();
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
        if (custom_font) SetTextureFilter(font.texture, TEXTURE_FILTER_BILINEAR);
    }
    return font;
}
void pl_font_close(void) {
    if (custom_font) UnloadFont(font);
    font = (Font){0}; custom_font = 0;
}
float pl_font_measure(const char *text, int size) {
    return MeasureTextEx(font, text, (float)size, 0).x;
}
void pl_font_draw(const char *text, float x, float y, int size, Color ink) {
    DrawTextEx(font, text, (Vector2){x, y}, (float)size, 0, ink);
}
