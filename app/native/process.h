#ifndef POWERLAUNCH_PROCESS_H
#define POWERLAUNCH_PROCESS_H
/* Generic process builder. IDs are opaque, checked handles, not foreign pointers.
 * All strings are UTF-8. start consumes the builder on success AND failure.
 * The returned error is borrowed until the next call on the same thread.
 * Arguments are literal argv entries; no shell is involved for executables. */
long long pl_process_new(const char *program);
const char *pl_process_arg(long long handle, const char *argument);
void pl_process_free(long long handle);
const char *pl_process_start(long long handle, const char *working_directory);
#endif
