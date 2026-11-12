# File.read scratch allocation survives task exit (Plum 0.0.41)

The backup ASan/LSan fixture found 659,456 bytes in six allocations originating
in `native_stdlib/file_shim.c:read_ensure` / `file_read_n` / `Os.File.read` after
worker shutdown. Files were closed explicitly or through owning handles.

The shim keeps a realloc-backed `_Thread_local` read buffer/capacity, but has no
thread-exit cleanup for that allocation. Task exit loses the last pointer, so
repeated short-lived readers leak per-thread scratch memory. This is evidence
about this native runtime allocation, not proof that Plum-owned values leak.

This standalone reproduction uses only Os.File and task/join, with explicit
file.close. Build through the pinned compiler with Clang ASan, then run LSan.
For example, invoke the pinned compiler with a PLUM_CC driver containing
`-fsanitize=address -fno-omit-frame-pointer` and `PLUM_NO_BUILD_CACHE=1`, then run
with `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 LSAN_OPTIONS=exitcode=23`.

Expected: no leaked scratch allocations after tasks join. On the affected runtime,
three task-local reads allocate scratch buffers that outlive those tasks. Set
`POWERLAUNCH_REPRO_MAIN_THREAD=1` for the control: the same reads run on the main
thread, where the TLS pointer remains reachable, so LSan does not report it as
an unreachable task-exit leak.

Powerlaunch temporarily uses a small owned, thread-confined streaming Reader
handle in `platform/reader.plum` and `native/stream_reader.c` for reads. Its 64 KiB
buffer and FILE are released together on drop. Writing/seeking/checked closing
still use Plum Os.File; ZIP logic, CRC and verification remain Plum. The backup
fixture asserts zero live readers and runs with ASan/LSan, without suppressions.

A proper reusable fix belongs in Plum's native file runtime (thread-exit ownership
or caller/handle-owned read buffers with a safe borrow/copy contract). No upstream
issue or sibling source change was made as part of this application change.
