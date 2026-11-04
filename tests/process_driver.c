#include "../app/native/process.h"
#include <stdio.h>
#include "utf8_args.h"

int main(int argc, char **argv) {
#ifdef _WIN32
    argv = test_utf8_argv(&argc);
    if (!argv) return 3;
#endif
    if (argc < 3) return 2;
    long long handle = pl_process_new(argv[1]);
    if (!handle) return 3;
    for (int i = 3; i < argc; i++) {
        const char *error = pl_process_arg(handle, argv[i]);
        if (*error) { fprintf(stderr, "%s\n", error); pl_process_free(handle); return 4; }
    }
    const char *error = pl_process_start(handle, argv[2]);
    if (*error) { fprintf(stderr, "%s\n", error); return 1; }
    return 0;
}
