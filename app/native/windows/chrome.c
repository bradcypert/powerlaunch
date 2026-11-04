/* Native Windows chrome preserves system hit testing, snapping and accessibility.
 * Keep Windows headers in this translation unit; their GDI names collide with
 * raylib's API. Unsupported DWM attributes simply retain the OS defaults. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dwmapi.h>
#include <shobjidl.h>

void pl_windows_prepare(void) {
    SetCurrentProcessExplicitAppUserModelID(L"bradcypert.Powerlaunch");
}

void pl_windows_style(void *handle) {
    HWND window = (HWND)handle;
    BOOL dark = TRUE;
    COLORREF caption = RGB(23, 26, 35), text = RGB(237, 240, 247), border = RGB(40, 46, 61);
    DwmSetWindowAttribute(window, 20, &dark, sizeof dark);
    DwmSetWindowAttribute(window, 35, &caption, sizeof caption);
    DwmSetWindowAttribute(window, 36, &text, sizeof text);
    DwmSetWindowAttribute(window, 34, &border, sizeof border);
}
