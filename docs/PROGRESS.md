# Implementation progress

## Scope

Milestone 1 is in progress. The agreed full product is in `SPEC.md`; the current
prototype is a vertical slice, not completion of that specification.

## Implemented

- Mise-managed Plum 0.0.41 with an explicit compiler version check and download
  checksums locked for Linux x64/arm64, macOS x64/arm64, and Windows x64.
- Plum library records, JSON encoding/decoding, title/tag search, favorites,
  title sorting, and library-entry removal.
- Versioned persistence with atomic file replacement through `Os.write_file`.
  Failed loads disable saving; malformed data is never silently replaced.
- Plum-owned window layout and state, cover grid/editor, metadata fields,
  file selection, managed artwork import, save/discard, and launch actions.
- Native raylib/raygui ABI adaptation, lazy cover loading with a 24-texture
  cache and downsampled GPU textures.
- A generic native detached-process builder with literal argv and per-child cwd.
  POSIX double-fork/exec reports setup failures back through a close-on-exec pipe.
  Windows uses wide-character CreateProcessW and ShellExecuteExW for shortcuts.
- Windows uses a Unicode native file picker that preserves `.lnk` paths and
  does not change the launcher's working directory. A wide-file callback handles
  Unicode artwork filenames at the raylib boundary.
- A Windows GitHub Actions workflow installs the locked Plum compiler using Mise,
  tests and builds in MSYS2 UCRT64, recursively packages runtime DLLs and notices,
  smoke-tests the bundle, and uploads downloadable artifacts and diagnostics.
  Workflow execution evidence is separate from local validation below.

## Validation

Verified on Linux during initial implementation:

- `mise run check` and `mise run build` pass with the pinned compiler.
- `mise run test`: seven Plum tests pass, covering metadata/argument round trips,
  invalid schemas/records/IDs/paths, search/removal, failed-save preservation,
  path helpers, and artwork surviving deletion of its original source.
- Native process integration passes: Unicode/spaced executable and cwd paths,
  literal and empty arguments, no shell interpretation, missing executable,
  invalid working directory, and a game completing after its launcher exits.
- An isolated Xvfb desktop renders the UI. The real-input UI integration test
  registers a game, saves tags and argument boundaries (including an empty
  argument), edits its title, launches `/bin/true`, and reloads
  the saved library. `build/library-smoke.png` captures the loaded library.
- All three native adapters cross-compile to Windows x64 object files using
  Zig's Clang-based cross toolchain. This caught and resolved missing COM header
  declarations and a portability issue in the dialog dependency. This checks
  native source compilation, not full application linking or execution.

The [successful Windows CI run](https://github.com/bradcypert/powerlaunch/actions/runs/41893481130)
passes all seven Plum tests, the real process integration checks (including
Unicode executable/cwd paths), compilation, recursive DLL packaging, and a window
render/exit check. The artifact contains `powerlaunch.exe`, `glfw3.dll`,
`libraylib.dll`, `libwinpthread-1.dll`, build metadata, and license notices.

The hosted runner has no OpenGL driver, so CI supplies Mesa/llvmpipe only to a
disposable test copy. The uploaded bundle was inspected and contains no Mesa
DLLs; it uses the user's normal Windows graphics driver. Its screenshot was
visually inspected. macOS execution, normal Windows GPU validation, shortcut
integration, and clean-machine/manual interaction tests remain outstanding.

## Still required for milestone 1 / product completion

- Manual Windows GPU/desktop checks, shortcut preservation, and clean-machine
  runtime packaging. CI now verifies compilation, Unicode process paths and
  arguments, and a software-rendered packaged window.
- Thorough keyboard navigation, button focus, screen-reader accessibility,
  international font/input coverage, IME, and real multi-monitor/high-DPI checks.
- Multiline description editing and a friendly row-per-argument editor. Prototype
  fields are single-line and cap editable input at 16 KiB per field; longer
  existing values remain unchanged rather than being truncated.
- Unsaved-change confirmation on window close. Current save/discard protection
  applies when switching records, not exiting.
- Distinct read-only detail view, explicit tag filters, alternative sort options,
  missing-target relocation flow, and fully responsive layouts at large scaling.
- Artwork decode errors in the UI, persistent disk thumbnails, shared artwork
  reference tracking, and orphan cleanup. Current imports keep old artwork to
  avoid deleting data still needed after a failed save; removal retains covers.
- Full backup/restore with artwork, automatic pre-restore backup, schema
  migrations, recovery controls, and concurrent-instance conflict handling.
- Benchmark a few thousand games. Current search and sort are synchronous.
- Pin raylib for release builds and test native dependency bundling/licensing.
- Propose reusable cwd/detached-process functionality upstream in Plum after
  validating API and ownership semantics independently of this application.
