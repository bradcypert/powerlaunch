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
- A cohesive library-first design, shared button/typography/color tokens in Plum,
  explicit detail/edit views, tag/sort menus, and visible keyboard focus.
- Original SVG branding, embedded multi-size Windows ICO/version resources,
  runtime window icon, stable Windows app identity, and a dark native caption.
  Standard Windows caption controls and snapping behavior are preserved.
- Friendly argument rows, save/discard/cancel on unsaved navigation/window close,
  target relocation, and invalid/unavailable-artwork feedback.
- Cached search/filter/sort results, so an idle frame does not repeatedly rebuild
  the library. Queries are recomputed on relevant model/filter changes.
- OS-level memory reports, a bounded cover-cache stress workload, and a
  graphics-free ASan/LSan ownership workload using production model operations.
  Linux and Windows CI retain diagnostics; see `MEMORY.md`.
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
visually inspected. The maintainer subsequently confirmed adding a game,
launching it, adding artwork, and game survival after launcher closure on a real
Windows machine. The redesigned caption/icon and broader manual interaction
checks still need desktop validation. macOS execution and shortcut integration
remain outstanding.

## Design and memory pass

- Eight Plum tests and the process integration checks pass locally.
- Real-input UI tests cover registration, the separate detail/editor views,
  literal/empty argument rows, tag/sort menus, keyboard selection, Play, and
  save/cancel behavior when navigating away or closing a dirty editor.
- Native Windows chrome adapters cross-compile, and the actual linked PE icon
  resource is verified by packaging rather than relying on a source-file check.
- The graphics-free 250-cycle/100-game ASan/LSan workload passed locally without
  invalid-access or leak findings. Short working-set tests and the bounded cache
  test are recorded in `MEMORY.md`; none establishes universal leak freedom.
- Upstream opportunities and issue links are tracked in `PLUM-CANDIDATES.md`.
- [Design-pass CI](https://github.com/bradcypert/powerlaunch/actions/runs/41904981216)
  passed both the Windows packaging/window/memory job and the Linux sanitizer
  job. The linked Windows executable's icon resources were verified. The Windows
  2,000-game memory sample peaked near 98.5 MiB working set with 4 KiB growth
  after warm-up; see `MEMORY.md` for definitions and limits.

## Still required for milestone 1 / product completion

- Manual Windows verification of the new icon/caption, shortcut preservation,
  and clean-machine runtime packaging. CI verifies compilation, Unicode process
  paths and arguments, and a software-rendered packaged window.
- Thorough keyboard navigation, button focus, screen-reader accessibility,
  international font/input coverage, IME, and real multi-monitor/high-DPI checks.
- Multiline description editing. Text fields are currently single-line and cap
  editable input at 16 KiB per field; longer
  existing values remain unchanged rather than being truncated.
- Fully responsive layouts at large scaling and further missing-target/shortcut
  edge cases on real Windows machines.
- Persistent disk thumbnails, shared artwork
  reference tracking, and orphan cleanup. Current imports keep old artwork to
  avoid deleting data still needed after a failed save; removal retains covers.
- Full backup/restore with artwork, automatic pre-restore backup, schema
  migrations, recovery controls, and concurrent-instance conflict handling.
- Extend the 2,000-game memory measurements to longer sessions, richer artwork,
  launch/repair workflows, and 5,000-game response-time benchmarks. Search/sort
  are cached but synchronous when their inputs change.
- Pin raylib for release builds and test native dependency bundling/licensing.
- Propose reusable cwd/detached-process functionality upstream in Plum after
  validating API and ownership semantics independently of this application.

## Workflow, storage, and widget refactor

- `workflow` owns typed screens and navigation destinations, dirty-draft decisions,
  save/discard/cancel transitions, and successful-save continuation. Confirmation
  carries its destination rather than combining independent integer mode flags.
- `storage` owns opening/recovery state, metadata commits, managed-cover import
  rollback, removal, and managed artwork paths. Failed commits return errors
  without replacing the caller's in-memory library. Recovery stores reject writes.
  The versioned JSON format and retention of existing/shared covers are unchanged.
- `desktop` owns named typography/button roles and common interaction behavior.
  Enabled buttons/cards request a pointer, editable fields request an I-beam, and
  noninteractive or disabled regions restore the arrow. Font resources and matching
  draw/measure behavior live in a separate native typography adapter.
- Keyboard opening consumes that activation before rendering details, replacing
  the special negative focus ID that previously prevented accidental Play.
- Twelve Plum tests and native process integration pass. The expanded real-input
  UI test checks displayed cursor images, modal background controls, failed-save
  draft retention, Enter/Play separation, and existing registration/edit/reload.
- The expanded 250-cycle sanitizer workload exercises pure navigation and managed
  artwork commits/reloads as well as filtering and JSON; no ASan/LSan findings.
- Small-text rasterization intentionally remains unchanged during this refactor.
  Windows native-size/DPI comparisons and icon redesign remain follow-up work.

## Clipboard covers

- The editor offers Paste cover and Ctrl+V while the cover area or cover controls
  have keyboard focus. Text fields paste text locally; image shortcuts do not
  replace text-field behavior.
- Clipboard images are converted to PNG through a small raylib adapter and copied
  into Plum Bytes. A Plum handle releases the native PNG buffer deterministically.
  Supported image capture: Windows and the tested raylib X11 Linux backend.
  macOS/native Wayland image paste remains unsupported; Choose cover still works.
- Pasted PNGs are staged under the library's `drafts/` directory. Replacing,
  discarding, saving, and normal closing release the old draft. No game-folder
  file is written until Save. A crash can leave a draft file for future cleanup.
- Save retains the existing managed-library artwork and also creates
  `powerlaunch_cover.png` beside an executable. Existing names are never replaced;
  subsequent files use `powerlaunch_cover-2.png`, etc. Create-new OS writes prevent
  accidental overwrite even if another process creates the file concurrently.
- For `.lnk` entries, the configured working directory supplies the game folder;
  we do not write next to a shortcut on the Desktop. Missing/unwritable folders
  keep the managed cover and show a library-only notice. Metadata-save failure
  rolls back newly created managed/export copies while retaining the draft.
- Fifteen Plum tests cover normal persistence plus pasted artwork collisions,
  draft lifetime, rollback, and unavailable/unknown game-folder fallback.
- Xvfb integration exercises a real PNG clipboard, button/focused-keyboard paste,
  text clipboard behavior, replacement/discard cleanup, and both saved copies.
- A native clipboard fixture repeats PNG encode/decode/release 50 times. Windows
  CI uses actual CF_DIB clipboard data; ordinary local tests inject the getter to
  leave the desktop clipboard alone (opt in with POWERLAUNCH_TEST_SYSTEM_CLIPBOARD=1).
- The sanitizer workload includes pasted-cover staging/export/commit/cleanup and
  the native clipboard ownership fixture. Actual Windows desktop/browser clipboard
  checks and broader formats remain useful follow-up coverage.
