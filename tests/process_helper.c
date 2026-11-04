#include <stdio.h>
#include <stdlib.h>
#include "utf8_args.h"
#ifdef _WIN32
#include <direct.h>
#include <windows.h>
#define getcwd _getcwd
#define delay() Sleep(350)
#else
#include <unistd.h>
#define delay() usleep(350000)
#endif

int main(int argc, char **argv) {
#ifdef _WIN32
    argv = test_utf8_argv(&argc);
    if (!argv) return 3;
#endif
    if (argc < 2) return 2;
    delay(); /* The spawning launcher must have exited before this writes. */
#ifdef _WIN32
    wchar_t filename[32768];
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, argv[1], -1, filename, 32768)) return 3;
    FILE *output = _wfopen(filename, L"wb");
#else
    FILE *output = fopen(argv[1], "wb");
#endif
    if (!output) return 3;
    char directory[8192];
#ifdef _WIN32
    wchar_t working[32768];
    if (!_wgetcwd(working, 32768)) return 4;
    if (!WideCharToMultiByte(CP_UTF8, 0, working, -1, directory, sizeof directory, NULL, NULL)) return 4;
#else
    if (!getcwd(directory, sizeof directory)) return 4;
#endif
    fprintf(output, "%s\n", directory);
    for (int i = 2; i < argc; i++) fprintf(output, "%s\n", argv[i]);
    return fclose(output) != 0;
}
