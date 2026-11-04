#include <stdio.h>
#include <time.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commdlg.h>
#include <process.h>
#else
#include <unistd.h>
#include "../vendor/tinyfiledialogs.inc"
#endif

const char *pl_pick_file(long long artwork) {
#ifdef _WIN32
    static wchar_t filename[32768];
    static char utf8[131072];
    filename[0] = 0;
    OPENFILENAMEW dialog = {0};
    dialog.lStructSize = sizeof dialog;
    dialog.hwndOwner = GetForegroundWindow();
    dialog.lpstrTitle = artwork ? L"Choose cover image" : L"Choose game executable or shortcut";
    dialog.lpstrFilter = artwork
        ? L"Cover images\0*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tga\0All files\0*.*\0"
        : L"Games and shortcuts\0*.exe;*.lnk\0All files\0*.*\0";
    dialog.lpstrFile = filename;
    dialog.nMaxFile = sizeof filename / sizeof filename[0];
    dialog.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST
        | OFN_NOCHANGEDIR | OFN_NODEREFERENCELINKS | OFN_DONTADDTORECENT;
    if (!GetOpenFileNameW(&dialog)) return "";
    if (!WideCharToMultiByte(CP_UTF8, 0, filename, -1, utf8, sizeof utf8, NULL, NULL)) return "";
    return utf8;
#else
    const char *images[] = {"*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.tga"};
    const char *result = tinyfd_openFileDialog(artwork ? "Choose cover image" : "Choose game executable",
        "", artwork ? 6 : 0, artwork ? images : NULL, artwork ? "Cover image" : NULL, 0);
    return result ? result : "";
#endif
}

const char *pl_unique_token(void) {
    static unsigned long counter;
    static char result[96];
#ifdef _WIN32
    unsigned long pid = (unsigned long)_getpid();
#else
    unsigned long pid = (unsigned long)getpid();
#endif
    snprintf(result, sizeof result, "%llx-%lx-%lx", (unsigned long long)time(NULL), pid, ++counter);
    return result;
}
