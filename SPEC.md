# Powerlaunch specification

Status: agreed product scope; implementation begins with milestone 1.

## Purpose

A local desktop library for installed games that do not belong to a major
launcher: extracted itch.io downloads, older CD-ROM games, and other standalone
titles. Build for the maintainer's own collection first. Windows is the first
release platform; preserve a path to Linux and macOS.

## Product requirements

1. Register an already installed game by selecting an executable or a Windows
   `.lnk` shortcut. Suggest a title, then let the user review and save it.
2. Keep one launch configuration per game: target, argument array, and optional
   working directory. Default an executable's working directory to its parent.
   Preserve a shortcut's existing configuration unless explicitly overridden.
3. Store editable title, cover, description, release year, developer, custom
   tags, and favorite status. Only title and launch target are required.
4. Copy chosen artwork into managed storage. Moving the source image must not
   break the library. Show a title-based placeholder when artwork is absent.
5. Provide a dark landscape-cover grid (16:9 artwork slots), title search, sorting, favorites, tag
   filters, and a detail view with Play and Edit. Use mouse and keyboard controls,
   visible focus, readable text, scrolling, and display scaling.
6. Keep the launcher responsive and open when a game starts. Games must survive
   launcher closure. Never change the launcher's process-wide working directory
   to launch a game. Launch errors must explain what failed and how to fix it.
7. Retain missing targets and offer executable relocation without losing metadata.
8. Work offline without accounts. Use per-user application data and a versioned
   library format with safe writes and explicit handling of malformed/newer data.
9. Export metadata and managed artwork, excluding game installations. Restore
   replaces the library after confirmation and an automatic backup. Missing game
   paths remain repairable entries. Never overwrite the only recoverable copy.
10. Remove from library deletes only the record and its unreferenced managed
    artwork. Optional deletion of game files is future work.
11. Remain responsive with a few thousand entries through visible-item rendering,
    bounded artwork caching, thumbnails, and lazy loading. Measure before adding
    more elaborate indexing or concurrency.
12. Distribute the Windows release as a ZIP with everything required to run it.
    End users must not need Plum, Clang, or other development tools.

## Technology constraints

- Write domain logic, persistence, UI composition, and interactions in Plum.
- Pin the Plum compiler with Mise; do not depend on the developer's global Plum.
- Start with raylib/raygui through narrow C ABI adapters. Put direct foreign calls
  behind `unsafe` wrappers, not throughout application code.
- Generic native adapters must not own game records or application workflows.
- Where Plum lacks generally useful functionality, design separately testable
  library/runtime improvements suitable for upstream. A local native process
  adapter may establish behavior before upstream integration; document that debt.
- Keep platform-specific launching and dialogs behind one interface. C adapters
  are currently required for raylib's float/color structs and native OS handles.
- Provisionally use JSON with a schema version, stable string IDs, argument arrays,
  and managed artwork paths relative to library storage. Reject invalid data rather
  than silently resetting it. SQLite is not required for the initial collection.

## Milestones and acceptance

### 1. Feasibility / first vertical slice

- Reproducible Mise compiler setup and documented native prerequisites.
- Compile a Plum-owned raylib/raygui window.
- Register, edit, save, and reload a game, including Unicode and spaced paths.
- Choose and display local artwork; demonstrate a managed copy.
- Exercise keyboard focus/text editing, scrolling, and scaling.
- Launch with literal argument boundaries and a child-specific working directory.
- Verify successful launch, missing executable, invalid cwd, and child survival
  after launcher exit. Windows shortcuts preserve their existing settings.
- Test persistence round trips, malformed/newer versions, and failed saves.
- Windows build/run evidence is required to pass this milestone. Linux execution
  is useful development evidence, not a substitute for Windows validation.
- Reconsider the GUI toolkit if text, navigation, scaling, or accessibility costs
  are excessive. Do not call a functioning render loop a completed desktop UI.

### 2. Complete local library

Implement all metadata, grid/detail/edit flows, search/sort/filter/favorites,
relocation, safe removal, artwork lifecycle, and versioned persistence. Validate
against real older games and a synthetic few-thousand-entry library.

### 3. Recovery and Windows distribution

Implement full backup/restore, automatic pre-restore backup, migration/recovery
tests, and a self-contained Windows ZIP. Verify on a clean Windows installation.

### 4. Other desktop platforms

Package and validate Linux and macOS. Supporting the launcher on an OS does not
promise that games for another OS will run there.

## Deferred

Installer/disc-image/patch/uninstall management; scanning directories; external
launcher imports; automatic metadata/artwork lookup; ROM/emulator or Wine setup;
multiple launch profiles; playtime tracking; achievements; cloud sync; accounts;
portable storage mode; controller/couch mode; elaborate themes/animations; setup
wizards and automatic updates. File deletion may later be explicitly opt-in.

## Prototype visual direction

A quiet charcoal library with muted blue selection and warm white text. Portrait
artwork provides the color. Left-aligned text, a compact navigation rail, a
searchable central shelf, and a selected-game detail/editor panel. Use consistent
sentence-case actions: Add game, Save changes, Play, Remove from library.
Palette: canvas #181C24, surface #232A36, text #EEF0F4, secondary #AAB5C6,
selection #819BCB, error #E7A097. Use the toolkit's bundled font initially; verify
Unicode rendering and choose a properly licensed font before release.

## Open engineering evidence

Window/toolkit feasibility, Windows packaging, shortcut behavior, international
text input, accessibility, and high-DPI behavior remain validation tasks. Their
presence in the spec does not imply they are implemented. Track evidence and
remaining work in `docs/PROGRESS.md`.
