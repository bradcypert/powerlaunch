# Plum upstream candidates

The following issues were filed after the workflow/storage/widget refactor and
local validation. No Plum implementation changes were made. Library-specific
rendering and Powerlaunch workflows remain here; measurements are not proof of
language-wide guarantees.

| Item | Upstream issue |
| --- | --- |
| Detached processes and per-child cwd | [#435](https://github.com/bradcypert/plum/issues/435) |
| Prebuilt objects and compiler-driver arguments | [#436](https://github.com/bradcypert/plum/issues/436) |
| Live/peak allocation diagnostics and sanitizer workflow | [#437](https://github.com/bradcypert/plum/issues/437) |
| C scalar/layout coverage or generated bindings | [#438](https://github.com/bradcypert/plum/issues/438) |
| Bounded mutable native buffers and ownership contract | [#439](https://github.com/bradcypert/plum/issues/439) |
| Module aliases in qualified type annotations (new reproduction) | [#440](https://github.com/bradcypert/plum/issues/440) |

Issues include pinned source links, concrete application workarounds, design
tradeoffs, and acceptance tests. Existing ownership/counter/process discussions
are cross-linked rather than presented as new discoveries.

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
handles to Plum's closed extern scalar surface. Struct FFI already exists for
supported field types; C float/byte-sized fields are the relevant layout gap.
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

Plum already supports `Bytes.as_cstr`, `Bytes.from_cstr`, and opaque handles.
The request concerns bounded mutable native storage and its aliasing/borrow
contract, rather than re-adding binary FFI. An owned native-buffer abstraction
and documented callback/borrowed-string lifetimes could reduce scaffolding. Native
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

## Module alias type reproduction

Plum 0.0.41 accepts `geo.point()` after `use shapes as geo`, but rejects an
annotation `geo.Point` with `unknown type: geo.Point`. Changing just the
annotation to `shapes.Point` passes. Issue #440 contains the complete two-file
fixture and references the types requirement in the earlier alias issue #44.
Powerlaunch uses canonical module names for types while keeping function aliases.

## New candidate: exclusive file creation

Clipboard game-folder export needs to create a new file without replacing an
existing one, including the check/create race. `Os.write_bytes` provides atomic
replacement, which is a different operation. `app/native/exclusive_file.c` adds a
small UTF-8 create-new adapter (POSIX O_EXCL / Windows _O_EXCL), while filename
selection and rollback stay in Plum. A standard create-new Bytes write returning
AlreadyExists distinctly would remove this reusable C code. This is a newly
identified candidate, not an additional filed issue.

## New candidate: generated helpers for channel payloads with handles

Plum 0.0.41 accepts checking a channel payload struct containing an optional
owned handle, then fails linking because generated LLVM references a missing
string/equality helper. See the [minimal reproduction](plum-repros/channel-owned-handle/README.md).
Powerlaunch uses a direct handle channel with one outstanding request instead,
retaining deterministic destruction. This is a compiler correctness candidate,
not evidence of a runtime ownership failure. No issue filed yet.

## New candidate: atomic publication without replacing an existing path

Backup export stages and validates its ZIP beside the destination, then needs an
atomic publish that fails if the final name exists, including a race after review.
`Os.rename_file` replaces existing files, which cannot express this contract.
The small `pl_publish_new` adapter uses a Windows non-replacing move or Linux
`RENAME_NOREPLACE`, with an atomic hard-link fallback where supported. No ordinary
replacing rename or cross-volume copy fallback is allowed. Backup ZIP writing,
CRC and validation stay in Plum using existing streaming `Os.File` handles.

A reusable no-replace rename/publish operation with distinct AlreadyExists errors
would remove this C edge and complement the existing create-new write candidate.
The native save-file dialog is another reusable desktop-package concern. No new
Plum issue or sibling-repository change was made for this work.

## Backup validation: two minimized Plum 0.0.41 runtime/compiler defects

- [File.read task-exit cleanup](plum-repros/file-read-task/README.md): three
  short-lived tasks with explicit File.close leak 393,216 bytes of native TLS
  scratch allocation under LSan; the main-thread control exits cleanly. A small
  owned streaming-reader adapter works around this until runtime cleanup is fixed.
- [Struct literal field placement](plum-repros/struct-field-order/README.md): a
  reordered literal checks/builds, then crashes when a boolean slot is read as a
  String. The declaration-order control succeeds. Constructing backup records in
  declaration order avoids the issue.

These were discovered by the new headless sanitizer and real-input UI tests.
No new upstream issues or Plum source changes have been made. The application
fixtures keep both ownership and UI regression coverage.
