/* A real CF_DIB fixture, independent of raylib's clipboard reader. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <string.h>

static void set_clipboard(UINT format, const void *bytes, SIZE_T length) {
    HWND window = CreateWindowExW(0, L"STATIC", L"Powerlaunch clipboard fixture", 0,
        0, 0, 0, 0, HWND_MESSAGE, NULL, GetModuleHandleW(NULL), NULL);
    assert(window);
    int opened = 0;
    for (int i = 0; i < 50 && !opened; i++) { opened = OpenClipboard(window); if (!opened) Sleep(20); }
    assert(opened);
    assert(EmptyClipboard());
    HGLOBAL memory = GlobalAlloc(GMEM_MOVEABLE, length);
    assert(memory);
    void *data = GlobalLock(memory);
    assert(data);
    memcpy(data, bytes, length);
    GlobalUnlock(memory);
    assert(SetClipboardData(format, memory));
    CloseClipboard(); // Clipboard now owns memory.
    DestroyWindow(window);
}
void fixture_text(void) {
    const wchar_t text[] = L"No image here";
    set_clipboard(CF_UNICODETEXT, text, sizeof text);
}
void fixture_image(void) {
    struct { BITMAPINFOHEADER header; unsigned char pixels[16]; } dib = {0};
    dib.header.biSize = sizeof(BITMAPINFOHEADER);
    dib.header.biWidth = dib.header.biHeight = 2;
    dib.header.biPlanes = 1;
    dib.header.biBitCount = 32;
    dib.header.biCompression = BI_RGB;
    dib.header.biSizeImage = sizeof dib.pixels;
    for (int i = 0; i < 4; i++) dib.pixels[i * 4 + 2] = 255;
    set_clipboard(CF_DIB, &dib, sizeof dib);
}
