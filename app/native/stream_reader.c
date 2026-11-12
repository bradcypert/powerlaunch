/* Thread-confined owned streaming reader. Temporary workaround for Plum 0.0.41
 * File.read's thread-local scratch allocation surviving worker exit.
 * No archive policy or shared thread-local buffers live here. */
#if !defined(_WIN32)
#define _FILE_OFFSET_BITS 64
#endif
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdatomic.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

typedef struct { FILE *file; unsigned char data[65536]; } StreamReader;
static atomic_llong live_readers;
long long pl_reader_open(const char *path) {
    FILE *file = NULL;
#ifdef _WIN32
    int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, NULL, 0);
    if (!n) return 0;
    wchar_t *wide = calloc((size_t)n, sizeof *wide);
    if (!wide) return 0;
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, n)) file = _wfopen(wide, L"rb");
    free(wide);
#else
    file = fopen(path, "rb");
#endif
    if (!file) return 0;
    StreamReader *reader = malloc(sizeof *reader);
    if (!reader) { fclose(file); return 0; }
    reader->file = file;
    atomic_fetch_add(&live_readers, 1);
    return (long long)(intptr_t)reader;
}
long long pl_reader_read(long long raw, long long count) {
    StreamReader *reader = (StreamReader *)(intptr_t)raw;
    if (!reader || count <= 0 || count > (long long)sizeof reader->data) return -1;
    size_t n = fread(reader->data, 1, (size_t)count, reader->file);
    return !n && ferror(reader->file) ? -1 : (long long)n;
}
const char *pl_reader_data(long long raw) { return (const char *)((StreamReader *)(intptr_t)raw)->data; }
long long pl_reader_position(long long raw) {
    StreamReader *reader = (StreamReader *)(intptr_t)raw;
#ifdef _WIN32
    return _ftelli64(reader->file);
#else
    return (long long)ftello(reader->file);
#endif
}
void pl_reader_close(long long raw) {
    StreamReader *reader = (StreamReader *)(intptr_t)raw;
    if (!reader) return;
    fclose(reader->file); free(reader);
    atomic_fetch_sub(&live_readers, 1);
}
long long pl_reader_live(void) { return atomic_load(&live_readers); }
