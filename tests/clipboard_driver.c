/* Exercise actual Win32 clipboard data on Windows; on Linux inject only the
 * platform image getter, testing production encode/ownership without a GPU. */
#include <raylib.h>
#include <assert.h>
#include <stdint.h>
#include <string.h>
#if defined(_WIN32) && !defined(POWERLAUNCH_FAKE_CLIPBOARD)
void fixture_image(void);
void fixture_text(void);
#else
static int has_image;
void fixture_image(void) { has_image = 1; }
void fixture_text(void) { has_image = 0; }
Image GetClipboardImage(void) { return has_image ? GenImageColor(2, 2, RED) : (Image){0}; }
#endif
long long pl_clipboard_capture(void);
long long pl_clipboard_size(long long);
const char *pl_clipboard_data(long long);
const char *pl_clipboard_error(void);
void pl_clipboard_free(long long);

int main(void) {
    SetTraceLogLevel(LOG_WARNING);
    fixture_text();
    assert(pl_clipboard_capture() == 0);
    assert(strstr(pl_clipboard_error(), "image"));
    fixture_image();
    for (int i = 0; i < 50; i++) {
        long long image = pl_clipboard_capture();
        assert(image != 0);
        long long size = pl_clipboard_size(image);
        const char *data = pl_clipboard_data(image);
        assert(size > 8 && memcmp(data, "\x89PNG\r\n\x1a\n", 8) == 0);
        Image decoded = LoadImageFromMemory(".png", (const unsigned char *)data, (int)size);
        assert(decoded.data && decoded.width == 2 && decoded.height == 2);
        Color pixel = GetImageColor(decoded, 0, 0);
        assert(pixel.r > 200 && pixel.g < 100 && pixel.b < 100);
        UnloadImage(decoded);
        pl_clipboard_free(image);
    }
    fixture_text();
    assert(pl_clipboard_capture() == 0);
    return 0;
}
