# Powerlaunch

A Plum desktop launcher for the games already on your computer. Windows is the
first release target, with Linux and macOS planned. See [SPEC.md](SPEC.md) for the
agreed product requirements and [docs/PROGRESS.md](docs/PROGRESS.md) for evidence
and unfinished work. This is an early feasibility prototype, not a release.

## Windows downloads and CI

The [Windows build workflow](https://github.com/bradcypert/powerlaunch/actions/workflows/windows.yml)
runs on pushes to `main`, pull requests, and manual **Run workflow** requests.
It installs the checksum-locked Plum compiler through Mise and uses MSYS2 UCRT64
for Clang, Python, raylib, and native libraries. It runs the Plum/process tests,
builds `powerlaunch.exe`, and follows its PE imports to bundle transitive runtime
DLLs. Missing DLLs fail packaging instead of producing an incomplete download.

Open a successful run and download **powerlaunch-windows-x64** from **Artifacts**.
Extract the complete ZIP, keep its DLLs beside `powerlaunch.exe`, and run the
executable. You do not need Plum, Clang, Python, Mise, or MSYS2 to run that bundle.
These are unsigned development builds, retained for 30 days, rather than releases.

CI also renders and closes a copy of the packaged window with development tools
removed from `PATH`. Hosted runners lack an OpenGL display driver, so this test
adds Mesa software rendering to a disposable copy **after** producing the download.
Mesa DLLs are excluded from the downloadable bundle. Screenshots, logs, and the
package inventory are uploaded as **windows-build-diagnostics**. Test the download
on a normal Windows PC before treating it as a validated release.

## Development

Install [Mise](https://mise.jdx.dev/), Clang, Python 3.11+, raylib development files,
and pkg-config. Plum **0.0.41** is pinned in `mise.toml` using Mise's GitHub backend.
The scripts resolve `mise which plum` explicitly so an older global compiler
cannot shadow the project version.

```sh
mise trust
mise install github:bradcypert/plum
mise run check
mise run test
mise run build
mise run dev
```

The committed `mise.lock` pins the compiler download URLs and checksums for all
five supported desktop targets. Use `mise install --locked github:bradcypert/plum`
to require those locked assets.

`mise run dev` builds before opening the application. Development requires the
native prerequisites; a future release ZIP will bundle its runtime dependencies.

### Linux

Install your distribution's raylib development package and pkg-config. A
graphical file picker such as Zenity or KDialog is recommended: tinyfiledialogs
uses an available system helper. Text paths remain editable if no helper exists.
OpenGL and a working desktop display are needed to run the UI, not the unit tests.

### Windows

Use a MinGW/UCRT development environment (Plum's Windows release targets MinGW).
Install Clang, Python 3, pkg-config, and raylib for the same architecture/toolchain.
Run Mise tasks from that environment with `python3`, `clang`, and `pkg-config`
available. The build adds the Windows dialog/COM/shell libraries. Windows build
and UI validation remain required; Linux success is not Windows verification.

### macOS

Install Clang, Python 3, pkg-config, and raylib. The current build expects
pkg-config to find raylib, and tinyfiledialogs uses the system's dialog helper.
macOS execution and app-bundle packaging remain unverified.

## Using the library

The library opens as a cover shelf. Select a game (or use Tab, arrow keys, and
Enter) to see its details and Play button. **Edit game** opens a separate editor.
Tag and sorting controls open explicit choice lists; search also matches tags.
The native Windows caption adopts the dark theme and keeps standard window
controls, snapping and the system menu. The executable/window/taskbar use the
Powerlaunch icon and Windows app identity.

Choose **Add game**, browse to an installed executable (or a Windows `.lnk`), and
edit its title. **Choose cover** selects artwork; **Save changes** copies it into
the library and saves the entry. Select its card to open details, then choose
**Edit game** to make changes. **Play** starts the saved game independently.

Use **Add argument** for each launch argument; spaces stay within that row, and
an empty row represents an empty argument. Values are never interpreted by a shell.
A shortcut defaults to blank arguments and working directory, preserving the
shortcut's own settings. If you edit its target manually, review the working
directory as well. Paths should be absolute.

Tab/Shift+Tab moves among fields and buttons, Enter/Space activates a focused
button, Ctrl+F focuses library search, and Ctrl+S saves an editor. Escape returns
from details/editing. Use the mouse wheel over the library or editor form to
scroll. Dirty editors ask whether to save, discard, or keep editing before
navigation or window close. A failed save keeps the editor open. Removal asks
for a second click and keeps the game's files. Missing games offer **Locate game**.

Data defaults to `%LOCALAPPDATA%/Powerlaunch` on Windows,
`$XDG_DATA_HOME/powerlaunch` (or `~/.local/share/powerlaunch`) on Linux, and
`~/Library/Application Support/Powerlaunch` on macOS. Set `POWERLAUNCH_DATA_DIR`
to an absolute path for an isolated development library. Corrupt or unsupported
libraries open with saving disabled; the original file is preserved.

`POWERLAUNCH_UI_SCALE=1.5` overrides scale for development. Automated render
checks can set `POWERLAUNCH_SMOKE_FRAMES=3` and
`POWERLAUNCH_SCREENSHOT=/absolute/path.png` to render, capture, and exit.

On Linux, the optional real-input UI integration check uses Xvfb and libXtst:

```sh
mise run build
xvfb-run -a -s '-screen 0 1600x1000x24' python3 tests/ui_smoke.py
```

It uses a temporary library and launches only a harmless test executable.

Packaging dependency checks run on any platform:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

On Windows, `python3 scripts/package_windows.py` builds the artifact folder after
compilation. `python3 scripts/smoke_windows.py` checks that packaged application.

## Back up the library

Choose **Back up library** in the sidebar, then choose/type a new absolute ZIP
filename. **Review backup** checks the saved records and referenced covers;
**Start backup** writes and verifies the archive before publishing it. The screen
shows progress and offers cancellation. Existing destination files are never
replaced, including files created after review. A missing/unreadable cover fails
the export so an incomplete backup cannot be mistaken for a complete one.

Backups contain saved metadata and referenced managed artwork. Game installations,
saves, thumbnails and temporary drafts are excluded. Unsaved edits use the usual
Save/Discard/Keep editing flow before opening backup. An empty library can be
backed up. ZIP32 export is limited to less than 4 GiB and 65,532 unique covers.
The ZIP is unencrypted and retains the paths/arguments in your metadata.
Restore/migration UI is a separate upcoming feature. See [backup format and failure
behavior](docs/BACKUP.md).

## Memory checks and Plum integration

```sh
mise run memory             # 20-second, 2,000-game idle profile; needs a display
mise run memory-check       # Linux ASan/LSan check without graphics initialization
xvfb-run -a -s '-screen 0 1600x1000x24' python3 tests/ui_memory.py
xvfb-run -a -s '-screen 0 1600x1000x24' mise exec -- python3 tests/scroll_performance.py
```

`scripts/profile_memory.py --seconds 10 --games 2000 --covers 40` selects a custom
workload. Reports and logs are in `build/`. All workloads use isolated synthetic
libraries. Windows CI uploads working-set/private-commit samples; Linux CI runs
the ownership workload with address/leak sanitizers. These checks are evidence
for particular workloads, not a proof of Plum's guarantees across every program.

See [memory measurements](docs/MEMORY.md) and [Plum upstream candidates](docs/PLUM-CANDIDATES.md).
The latter are discussion notes; no upstream issues have been filed automatically.
Icon assets are checked in. To regenerate them from the SVG on a developer
machine with librsvg, run `python3 scripts/generate_icons.py`.

## Source layout

- `app/library/`: Plum records, validation, searching, JSON, atomic persistence.
- `app/platform/`: Plum storage paths, artwork copying, and process/dialog wrappers.
- `app/desktop/`: safe Plum wrapper surface around native widgets and rendering.
- `app/main.plum`: Plum application state, layout, navigation, and actions.
- `app/native/`: generic ABI adapters, dialogs, detached process launching.
- `app/vendor/`: pinned raygui and tinyfiledialogs sources and license notices.
- `tests/`: real process integration checks.

The process adapter is deliberately generic. Upstream candidates are a
child-specific working directory and an explicit detached-launch API. These
should be designed and tested separately in Plum; this project does not change
the sibling Plum checkout.

### Paste a cover

In Add/Edit game, click **Paste cover**, or click the cover preview and press
**Ctrl+V** after copying an image (for example, Copy image in a browser or a
screenshot). Paste previews the image; **Save changes** keeps it. Text fields
accept text paste instead. Empty/text-only clipboards leave the current cover
intact and show a message.

Saving creates a managed library copy and, when possible, `powerlaunch_cover.png`
in the executable's folder. An existing file is preserved and a numbered name is
used instead. Shortcuts use their configured working directory. If that directory
is unknown or unwritable, the cover stays in the library and a message explains
why there is no game-folder copy. Discarding the editor does not write game files.

Image paste is supported on Windows and tested on Linux/X11 with the selected
raylib backend. macOS/native Wayland image paste is not supported yet; use
**Choose cover** there. Accepted captures are limited to 16 megapixels and a
64 MiB encoded PNG; very large clipboard images can still require transient
memory while the backend decodes them.

Cover loading uses one Plum background worker and disposable thumbnails in
`thumbnails-v1/` beside `library.json`. It is safe to delete that cache while the
launcher is closed; originals remain in `artwork/`. It regenerates as needed and
currently has no automatic disk pruning. Cover decoding accepts images up to
16 megapixels; larger images should be resized before importing. GPU texture storage is bounded at
128 textures / 64 MiB of tracked pixels; this is not a total process-memory limit.
