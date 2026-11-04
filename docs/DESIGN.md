# Desktop design pass

The library is the primary screen. Editing is an intentional separate view.
Native window controls retain Windows resize, snap, system-menu and accessibility
behavior; the title bar adopts the application's dark colors.

## Visual system

- Canvas: ink `#171A23`; sidebar `#1C202B`; panels `#242A38`.
- Text: paper `#EDF0F7`; secondary slate `#A5AFC3`.
- Accent: soft iris `#B9A7F2`; actions use dark text on iris.
- Type: Segoe UI on Windows, Open Sans on Linux, system Arial on macOS.
  Sizes: 32 for page/game titles, 20 for sections, 17 for body, 14 for metadata.
- Geometry: 8 px spacing grid, restrained 5 px button corners, portrait 2:3 covers.
  Borders indicate focus/selection rather than enclosing every label.
- Identity: a simple P/play monogram, built as SVG and embedded into the executable
  and runtime window, so it works from any working directory.

## Layout

```text
Native dark title bar / application icon / Windows controls
Navigation       Library title                  Search / Add game
Library          Tag filter                     Sort
Favorites        Cover     Cover     Cover     Cover
                 Title     Title     Title     Title
                 Developer Developer Developer Developer
                 Status and keyboard hints

Navigation       Back to library
                 Cover       Game title / metadata
                             Play / Favorite / Edit
                             Description / tags / launch details

Navigation       Edit game                     Cancel / Save changes
                 Cover       Title / target / metadata fields
                             Launch options and arguments
```

The previous always-open form made every game feel like a settings record. The
revision gives artwork and titles the main space, with a quiet navigation rail
and a deliberate detail/editor transition. Empty states give one useful action;
there is no decorative dashboard, simulated activity, or animated background.

## Related progress items

This pass tackles the separate detail view, keyboard navigation, tag filtering,
sort options, target repair, unsaved-change protection, and artwork-error feedback.
Multiline editing, backup/restore, broad accessibility/IME coverage, persistent
thumbnail generation, and platform packaging beyond Windows remain tracked in
`PROGRESS.md`; they are not silently considered complete by the visual redesign.

## Memory and Plum boundary

Record the old and revised build with the same workload and graphics driver.
Track working-set/private memory, warm-up versus steady state, and cache capacity.
Process growth is a signal to investigate, not proof of a language-runtime leak.
Use sanitized builds and a graphics-free Plum workload to distinguish runtime
ownership issues from native adapters and driver allocations.

Generally useful C-heavy work is documented as an upstream candidate in
`PLUM-CANDIDATES.md`. Do not modify Plum or file issues without coordinating with
the maintainer; report concrete evidence and proposed reusable API boundaries.
