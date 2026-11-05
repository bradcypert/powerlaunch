/* A create-new write: never replaces an existing user file, including races. */
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <io.h>
#include <sys/stat.h>
#else
#include <unistd.h>
#endif

/* 0 written, 1 already exists, 2 other error. The byte pointer is borrowed. */
long long pl_write_new(const char *path, const char *bytes, long long length) {
    if (length < 0) return 2;
#ifdef _WIN32
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, NULL, 0);
    if (!count) return 2;
    wchar_t *wide = calloc((size_t)count, sizeof *wide);
    if (!wide) return 2;
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, count)) { free(wide); return 2; }
    int fd = _wopen(wide, _O_WRONLY | _O_CREAT | _O_EXCL | _O_BINARY, _S_IREAD | _S_IWRITE);
#else
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0666);
#endif
    if (fd < 0) {
        int result = errno == EEXIST ? 1 : 2;
#ifdef _WIN32
        free(wide);
#endif
        return result;
    }
    long long offset = 0;
    while (offset < length) {
        unsigned int chunk = (unsigned int)((length - offset > 32768) ? 32768 : length - offset);
#ifdef _WIN32
        int written = _write(fd, bytes + offset, chunk);
#else
        ssize_t written = write(fd, bytes + offset, chunk);
#endif
        if (written < 0 && errno == EINTR) continue;
        if (written <= 0) break;
        offset += written;
    }
#ifdef _WIN32
    int closed = _close(fd);
    if (offset != length || closed) _wunlink(wide);
    free(wide);
#else
    int closed = close(fd);
    if (offset != length || closed) unlink(path);
#endif
    return offset == length && closed == 0 ? 0 : 2;
}
