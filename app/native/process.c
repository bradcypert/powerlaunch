#include "process.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <objbase.h>
#include <shellapi.h>
#include <wchar.h>
#else
#include <fcntl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

#define BUILDERS 16
#define ARGUMENTS 256
typedef struct { char *argv[ARGUMENTS + 2]; int count; } Builder;
static Builder builders[BUILDERS];
static _Thread_local char error_text[512];

static const char *failure(const char *operation, unsigned long code) {
#ifdef _WIN32
    snprintf(error_text, sizeof error_text, "%s failed (Windows error %lu). Check the target and working directory.", operation, code);
#else
    snprintf(error_text, sizeof error_text, "%s: %s", operation, strerror((int)code));
#endif
    return error_text;
}
static Builder *get(long long h) {
    return h > 0 && h <= BUILDERS && builders[h - 1].count ? &builders[h - 1] : NULL;
}
long long pl_process_new(const char *program) {
    if (!program || !*program) return 0;
    for (int i = 0; i < BUILDERS; i++) if (!builders[i].count) {
        builders[i].argv[0] = strdup(program);
        if (!builders[i].argv[0]) return 0;
        builders[i].count = 1;
        return i + 1;
    }
    return 0;
}
const char *pl_process_arg(long long h, const char *argument) {
    Builder *b = get(h);
    if (!b) return "Invalid process builder.";
    if (b->count >= ARGUMENTS + 1) return "Too many launch arguments (maximum 256).";
    char *value = strdup(argument);
    if (!value) return "Not enough memory to prepare launch arguments.";
    b->argv[b->count++] = value;
    b->argv[b->count] = NULL;
    return "";
}
void pl_process_free(long long h) {
    Builder *b = get(h);
    if (!b) return;
    for (int i = 0; i < b->count; i++) free(b->argv[i]);
    memset(b, 0, sizeof *b);
}

#ifdef _WIN32
static wchar_t *wide(const char *s) {
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s, -1, NULL, 0);
    if (!count) return NULL;
    wchar_t *out = calloc((size_t)count, sizeof *out);
    if (out) MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, s, -1, out, count);
    return out;
}
/* Quote every argument using the MS C runtime argv convention. In particular,
 * double trailing backslashes before the closing quote and preserve empty args. */
static wchar_t *command_line(Builder *b, int from) {
    size_t capacity = 1;
    for (int i = from; i < b->count; i++) capacity += strlen(b->argv[i]) * 2 + 4;
    wchar_t *out = calloc(capacity, sizeof *out), *p = out;
    if (!out) return NULL;
    for (int i = from; i < b->count; i++) {
        wchar_t *arg = wide(b->argv[i]);
        if (!arg) { free(out); return NULL; }
        if (i > from) *p++ = L' ';
        *p++ = L'"';
        const wchar_t *s = arg;
        while (*s) {
            size_t slashes = 0;
            while (*s == L'\\') { slashes++; s++; }
            size_t copies = slashes * ((*s == L'"' || !*s) ? 2 : 1);
            while (copies--) *p++ = L'\\';
            if (*s == L'"') *p++ = L'\\';
            if (*s) *p++ = *s++;
        }
        *p++ = L'"';
        free(arg);
    }
    *p = 0;
    return out;
}
const char *pl_process_start(long long h, const char *cwd) {
    Builder *b = get(h);
    if (!b) return "Invalid process builder.";
    wchar_t *program = wide(b->argv[0]);
    wchar_t *directory = *cwd ? wide(cwd) : NULL;
    if (!program || (*cwd && !directory)) {
        free(program); free(directory); pl_process_free(h);
        return "Launch paths must be valid UTF-8.";
    }
    size_t n = wcslen(program);
    DWORD code = 0;
    if (n >= 4 && _wcsicmp(program + n - 4, L".lnk") == 0) {
        wchar_t *parameters = command_line(b, 1);
        SHELLEXECUTEINFOW info = {0};
        info.cbSize = sizeof info;
        info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_NO_UI;
        info.lpFile = program;
        info.lpParameters = b->count > 1 ? parameters : NULL;
        info.lpDirectory = directory;
        info.nShow = SW_SHOWNORMAL;
        HRESULT com = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
        if (!parameters) code = ERROR_NOT_ENOUGH_MEMORY;
        else if (!ShellExecuteExW(&info)) code = GetLastError();
        if (info.hProcess) CloseHandle(info.hProcess);
        if (SUCCEEDED(com)) CoUninitialize();
        free(parameters);
    } else {
        wchar_t *line = command_line(b, 0);
        STARTUPINFOW startup = {0}; startup.cb = sizeof startup;
        PROCESS_INFORMATION process = {0};
        if (!line) code = ERROR_NOT_ENOUGH_MEMORY;
        else if (!CreateProcessW(program, line, NULL, NULL, FALSE,
            CREATE_NEW_PROCESS_GROUP | CREATE_UNICODE_ENVIRONMENT,
            NULL, directory, &startup, &process)) code = GetLastError();
        else { CloseHandle(process.hThread); CloseHandle(process.hProcess); }
        free(line);
    }
    free(program); free(directory); pl_process_free(h);
    return code ? failure("Launch", code) : "";
}
#else
static void child_failure(int fd, int operation) {
    int detail[2] = {operation, errno};
    /* Only async-signal-safe operations between fork and exec. */
    ssize_t written;
    do { written = write(fd, detail, sizeof detail); } while (written < 0 && errno == EINTR);
    _exit(127);
}
const char *pl_process_start(long long h, const char *cwd) {
    Builder *b = get(h);
    if (!b) return "Invalid process builder.";
    int channel[2];
    if (pipe(channel) < 0) { int e = errno; pl_process_free(h); return failure("Create launch pipe", e); }
    if (fcntl(channel[1], F_SETFD, FD_CLOEXEC) < 0) {
        int e = errno; close(channel[0]); close(channel[1]); pl_process_free(h); return failure("Prepare launch pipe", e);
    }
    pid_t intermediate = fork();
    if (intermediate == 0) {
        close(channel[0]);
        if (setsid() < 0) child_failure(channel[1], 0);
        pid_t child = fork();
        if (child < 0) child_failure(channel[1], 0);
        if (child > 0) _exit(0);
        if (*cwd && chdir(cwd) < 0) child_failure(channel[1], 1);
        int nullfd = open("/dev/null", O_RDWR);
        if (nullfd < 0) child_failure(channel[1], 0);
        for (int fd = 0; fd < 3; fd++) if (dup2(nullfd, fd) < 0) child_failure(channel[1], 0);
        if (nullfd > 2) close(nullfd);
        execv(b->argv[0], b->argv);
        child_failure(channel[1], 2);
    }
    int fork_error = errno;
    close(channel[1]);
    if (intermediate < 0) {
        close(channel[0]); pl_process_free(h); return failure("Start process", fork_error);
    }
    int status;
    while (waitpid(intermediate, &status, 0) < 0 && errno == EINTR) {}
    int detail[2] = {0, 0};
    size_t total = 0;
    while (total < sizeof detail) {
        ssize_t n = read(channel[0], (char *)detail + total, sizeof detail - total);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { detail[0] = 0; detail[1] = errno; total = sizeof detail; break; }
        if (!n) break;
        total += (size_t)n;
    }
    close(channel[0]); pl_process_free(h);
    if (!total) return "";
    if (total != sizeof detail) return "Incomplete process launch response.";
    return failure(detail[0] == 1 ? "Open working directory" : detail[0] == 2 ? "Start executable" : "Detach process", detail[1]);
}
#endif
