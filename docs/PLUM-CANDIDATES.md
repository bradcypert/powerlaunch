# Plum upstream candidates

These are discussion notes, not filed issues or changes to Plum. Library-specific
rendering and Powerlaunch workflows remain in this project. Keep minimal repros
and measurements separate from assumptions about language guarantees.

## Detached processes and child-specific working directories

Evidence: `app/native/process.c` implements literal argv, a per-child cwd, launch
errors, and lifetime independence. Existing Plum `Process.Child` ownership kills
the child when its handle is dropped and options lack a per-child cwd. Changing
the whole process cwd would affect all other work and is not an acceptable substitute.

Proposed discussion: an explicit `Process.launch_detached(options)` and optional
cwd in process options. Preserve `Child`'s existing ownership behavior. Decide how
errors, environment, output handles and platform shortcut launching compose;
Windows `.lnk` integration may belong in a desktop package rather than Process.

## C ABI scalar and struct coverage / bindings tooling

Evidence: `app/native/ui.c` adapts raylib's `float`, byte colors, rectangles and
handles to Plum's currently closed `Int`/`Float`/`Bool`/`CStr` extern surface.
That adapter would be needed by other Plum applications using the same C APIs.

Proposed discussion: typed fixed-width C scalars/POD layout, or generated wrappers
from C headers. Preserve explicit unsafe boundaries and resource ownership. Do
not add game/UI behavior to the compiler. Generic rendering wrappers can become
a Plum raylib package independently of language-level changes.

## Runtime memory diagnostics

Evidence: `PLUM_RT_STATS` reports cumulative allocation counts/bytes, not live
allocations or ownership provenance. Process working set includes native code,
allocators and graphics drivers. Our memory sampler uses OS APIs and a separate
graphics-free workload uses Clang ASan/LSan against production Plum operations.

Proposed discussion: opt-in live/peak runtime counters, allocation category or
call-site attribution, and a documented sanitizer build mode. A growing RSS alone
is not a runtime bug report. Include a minimized failing workload and symbolized
sanitizer output if a concrete ownership defect is found.

## Native text buffers and resource ownership

Evidence: the raygui text API expects a mutable C buffer. The binding keeps one
16 KiB scratch buffer and immediately copies results back to Plum; application
records stay in Plum. Textures have a bounded native LRU and explicit cleanup.

Proposed discussion: an owned native-buffer abstraction and documented callback/
borrowed-string lifetimes could reduce repeated binding scaffolding. Native
resource wrappers should have deterministic release and must not hide raw handle
aliasing. This is a reusable FFI concern, not a reason to move editor state to C.

## Linking prebuilt native objects and resources

Evidence: embedding the Windows icon produces a COFF object with `windres`.
Plum exposes C source and library linking, but not a direct prebuilt-object input.
The build temporarily supplies that object in the compiler-driver prefix, using
a relative path because `PLUM_CC` is split on spaces rather than shell-quoted.

Proposed discussion: a portable `--link-object` option and/or manifest resource
inputs, with structured compiler arguments. This would support Windows resource
objects and other language-neutral native assets without driver-prefix workarounds.
