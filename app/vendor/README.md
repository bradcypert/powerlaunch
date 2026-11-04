# Vendored native dependencies

These files are pinned and retain their upstream license notices in the source.
They are native dependencies, not application logic.

| File | Source revision | SHA-256 |
| --- | --- | --- |
| raygui.h | raysan5/raygui `25c8c65a6e5f0f4d4b564a0343861898c6f2778b` (4.0) | `36491f2067a5ff18e366f950dde2945bbcf9f75c1ab560ff9c8ca3ab6c7d0145` |
| tinyfiledialogs.h | native-toolkit/libtinyfiledialogs `cc6b593c029110af8045826ce691f540c85e850c` | `598faa191a8505723be3d4884dda8b214f19b2f00b3db7cdfa323ddba7a8737e` |
| tinyfiledialogs.inc | same revision, upstream `tinyfiledialogs.c` | `59dcd02254a6dd443c9e0fb2e9260284b5fff498dae238eedf5409afd12bac6a` |

raygui is zlib licensed. tinyfiledialogs uses the zlib license. The `.inc`
extension prevents Plum from discovering the dialog implementation as a second
translation unit; `native/dialogs.c` includes it once. Sources live outside
`native/` because Plum reserves its subdirectories for target selection.

raylib is supplied by the development system, discovered through pkg-config.
Its version is currently not pinned; packaging must pin and bundle it before a
release. Native dependency installation is separate from compiler version control.
