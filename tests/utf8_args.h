#ifndef POWERLAUNCH_TEST_UTF8_ARGS_H
#define POWERLAUNCH_TEST_UTF8_ARGS_H
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdlib.h>
/* A narrow main() uses the active Windows code page. Exercise the launcher's
 * Unicode API rather than accidentally testing that code-page conversion. */
static char **test_utf8_argv(int *argc) {
    wchar_t **wide = CommandLineToArgvW(GetCommandLineW(), argc);
    if (!wide) return NULL;
    char **args = calloc((size_t)*argc + 1, sizeof *args);
    if (!args) { LocalFree(wide); return NULL; }
    for (int i = 0; i < *argc; i++) {
        int bytes = WideCharToMultiByte(CP_UTF8, 0, wide[i], -1, NULL, 0, NULL, NULL);
        args[i] = calloc((size_t)bytes, 1);
        if (!args[i]) { LocalFree(wide); return NULL; }
        WideCharToMultiByte(CP_UTF8, 0, wide[i], -1, args[i], bytes, NULL, NULL);
    }
    LocalFree(wide);
    return args;
}
#endif
#endif
