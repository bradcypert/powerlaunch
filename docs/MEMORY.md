# Memory validation

The goal is to observe the application over time and collect evidence for Plum's
ownership behavior. A stable working set is not proof of language-level memory
safety; cumulative allocated bytes are not live memory.

## First baseline, Linux

Measured in the same development environment, with Plum 0.0.41 debug builds,
raylib 6.2, software OpenGL, 2,000 synthetic games, no cover files, and 600 frames
(about 10.3 seconds including startup). Reports are generated in `build/`.

| Metric | Previous always-open editor | Library-first/cached build |
| --- | ---: | ---: |
| Peak resident memory | 108.10 MiB | 108.02 MiB |
| Plum cumulative allocations | 17,001,121 | 743,138 |
| Plum cumulative allocated bytes | 901.72 MiB | 148.08 MiB |
| RSS change after 3-second warm-up | -1.21 MiB | 0.00 MiB |

Caching search/filter/sort results removed repeated idle-frame work: cumulative
allocated bytes fell **83.58%**, with no material peak-RSS reduction. The newer
resident-private sample rose about 1.95 MiB; do not label this a heap leak based
on one short observation. Resident-private pages also include file mappings
whose sharing/accounting can change when other graphics processes exit.

The longer native/UI workload cycles through a 2,000-game library and 40 test
covers, repeatedly entering/exiting details and editing. The cover cache stayed
within **24 textures / 14.06 MiB of tracked texture data**, with all tracked handles
released on close. The first 12-cycle sample peaked at **127.86 MiB RSS** and
finished about **0.66 MiB above** the first post-warm-up sample; later cycles
plateaued rather than increasing on every repetition. Private-resident accounting
changed more while another graphics test exited, so subsequent reports also
record anonymous resident bytes. Texture-size accounting excludes fonts, the app
icon, driver caches, allocator retention, and other GPU allocations.

## Ownership checks

`mise run memory-check` builds the application using Clang AddressSanitizer with
leak detection and runs 250 cycles of real model operations over 100 games:
editing, filtering, sorting, JSON encoding/decoding, atomic save and reload. It
does not initialize the graphics driver. The initial workload passed with no
ASan/LSan findings; about 552 MiB was cumulatively allocated during that run.

LeakSanitizer needs to inspect its own threads. The local sandbox cannot always
allow this; use an ordinary development shell. Linux CI grants the inspection
capability only inside its ephemeral container and does not alter host settings.
A sanitizer setup failure is a failed check, not a pass with leak detection off.

## Windows CI baseline

The [first design-pass Windows run](https://github.com/bradcypert/powerlaunch/actions/runs/41904981216)
passed the packaged-window check and the 2,000-game, ten-second memory profile.
Working set peaked at **98.52 MiB**; working-set and private-commit growth after
warm-up were each **4 KiB**. It recorded 944,366 cumulative Plum allocations /
152.90 MiB of cumulative allocated bytes. This run uses CI-only Mesa and a
different font/layout from Linux, so compare future Windows runs with this
workload rather than treating the OS totals as interchangeable.

The same run passed the graphics-free ASan/LSan workload in the Linux container.
These are short regression baselines; ordinary Windows desktop/high-DPI checks
and longer real-game sessions remain useful next steps.

## Reproduce and keep monitoring

```sh
mise run build
python3 scripts/profile_memory.py --seconds 20 --games 2000
python3 scripts/profile_memory.py --seconds 20 --games 2000 --covers 40
mise run memory-check
xvfb-run -a -s '-screen 0 1600x1000x24' python3 tests/ui_memory.py
POWERLAUNCH_MEMORY_UI_CYCLES=12 xvfb-run -a -s '-screen 0 1600x1000x24' python3 tests/ui_memory.py
```

The sampler creates a temporary library, records a binary hash, samples every
200 ms, and reports startup peak and changes after warm-up. Linux reports RSS,
resident-private clean/dirty pages, and anonymous resident pages. Windows reports
working set and private **committed** bytes via `GetProcessMemoryInfo`; these
private metrics are not directly comparable across operating systems.

Each Windows CI run profiles the packaged application with 2,000 synthetic games
and retains `windows-memory.json`/`.log` in the diagnostics artifact. CI's Mesa
renderer is added only to a disposable test copy and inflates working set relative
to hardware rendering; it is not part of the download. Linux CI retains the
graphics-free sanitizer log. Compare like workloads, builds, drivers and machines.

Use longer repetitions if a trend grows, then separate model-only and GUI/native
workloads. Minimize a reproducible ownership failure before attributing it to
Plum or filing an issue. Current upstream discussion notes live in
`PLUM-CANDIDATES.md`; the measurements so far have not established a Plum leak.

## Refactor validation (2026-11-04)

The workflow/storage/widget refactor passed the expanded graphics-free 250-cycle
ASan/LSan workload: 100 games, dirty-navigation confirmations, managed-cover
commits/reloads, and edit/filter/sort/JSON operations. It recorded 13,302,842
cumulative allocations / 580,163,607 cumulative bytes; these are not live totals.
This workload adds navigation and storage work, so its allocation totals are not
an identical-workload comparison with the earlier model-only run.

A ten-second Linux llvmpipe profile with 2,000 games and 40 available covers peaked
at 120,467,456 bytes RSS (114.9 MiB). After warmup, RSS and anonymous RSS each grew
by zero; resident-private pages grew by 3,125,248 bytes. The cache reached ten
textures / 6,144,000 tracked texture bytes and released all textures on close.
As before, private-page changes alone do not establish a heap leak. Diagnostics
are retained locally in `build/memory-profile.json` and `memory-sanitizer.log`;
Windows CI provides the platform-specific follow-up measurement.

## Clipboard ownership checks

The sanitizer check now exercises pasted-cover staging, create-new export,
metadata commit, draft cleanup and reload in the production Plum workload.
It also runs fifty native PNG capture/decode/release cycles and fifty calls through
`clipboard.image`, including the actual Plum handle and `Bytes.from_cstr` copy-out.
The latter uses an injected 320x480 image getter to avoid clipboard/display/GPU
state. All ran cleanly under ASan/LSan locally; native clipboard conversion is
separately exercised with actual CF_DIB data in Windows CI and real PNG selection
in the Xvfb UI test. Native capture and encoded PNG buffers are released before
the UI retains only the staged file and its bounded cached preview texture.

Captures above 16 megapixels or 64 MiB encoded PNG are rejected. The backend may
allocate decoded image memory before the dimension check; these are accepted
image limits, not a promise about peak process memory for arbitrary clipboard data.
