# Library backup format, version 1

Back up library exports the saved collection visible in the current launcher
instance. It includes game records (stable IDs, target/cwd/arguments and editable
metadata) and every distinct referenced file in managed `artwork/` storage.
A missing or unreadable cover fails the export; it is never silently omitted.

Game installations, save data, thumbnails, unreferenced artwork and temporary
clipboard drafts are excluded. This is an unencrypted local backup and retains
the paths and arguments stored in the library. Restore/migration UI is tracked
separately in [#10](https://github.com/bradcypert/powerlaunch/issues/10).

## Container

The file is a standard ZIP32 archive with UTF-8 entry names, stored/uncompressed
payloads, CRC-32 checksums and one central directory. PNG/JPEG artwork is already
encoded; the first implementation prioritizes bounded streaming and simple
interoperability over additional compression. It requires no external archiver.
The ZIP writer, CRC computation, planning, validation and worker protocol are Plum.
Writes/seeks use Plum File handles. Reads temporarily use an owning native
stream-reader adapter because Plum 0.0.41 leaks File.read scratch buffers at task
exit; the minimal reproduction is documented below.
See the [PKWARE ZIP specification](https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT).

Entries are:

```
backup.json
library.json
artwork/<managed filename>
```

`backup.json` is first. The manifest is UTF-8 JSON:

```json
{
  "format": "powerlaunch-library-backup",
  "version": 1,
  "library": "library.json",
  "library_schema_version": 1,
  "games": 3,
  "covers": 2,
  "excluded": ["game installations", "game saves", "thumbnails", "temporary drafts"]
}
```

`library.json` uses the existing schema-v1 encoder and decoder. Cover references
remain managed basenames; each nonempty reference maps to exactly one
`artwork/<basename>` entry, even when several games share it. Paths containing
separators, traversal names, drive markers or NUL are rejected by library
validation. No directory scanning is used to select content. The manifest,
library and selected artwork are the only entries. Empty libraries are valid.

Version 1 limits the complete archive to less than 4 GiB and 65,534 total entries
(65,532 unique covers plus manifest and library). Encoded filenames must fit ZIP's
16-bit name length. Unsupported sizes/counts fail before writing. Compression,
ZIP64, encryption and restoring third-party ZIPs are outside this implementation.
Stored ZIP timestamps are fixed at 1980-01-01; source file modes and timestamps
are not preserved. The backup preserves library semantics and artwork bytes.

## Export transaction

1. Choose/type a new absolute `.zip` filename. A missing `.zip` extension is added.
2. A Plum worker validates the captured library and checks referenced cover files.
   Review the game/unique-cover counts and explicit exclusions before Start backup.
3. Create an exclusively named sibling `.powerlaunch-backup-<token>.partial/`
   staging directory, then stream `backup.zip` into it. File payloads use at most
   64 KiB read buffers; metadata/entry records remain in memory.
4. Close the output with error checking. Reopen it and verify every local header,
   payload CRC/size, central-directory record, end record and EOF against the
   captured export plan. This verifies this application's own output; it is not
   an untrusted archive extraction API.
5. After a final cancellation checkpoint, atomically publish the verified file
   without replacing an existing destination, including one created after review.
   Windows uses a non-replacing same-volume move; Linux uses no-replace rename,
   with a no-replace hard-link fallback where available. There is no replacing
   rename or cross-volume copy fallback.
6. Remove the staging directory. A cleanup failure after successful publication
   reports a valid saved backup with a cleanup notice, rather than claiming that
   publication failed.

Checking, writing and verification progress use a bounded request/acknowledgement
protocol: one event is outstanding, and the worker waits for UI acknowledgement.
No file bytes are queued through channels. Cancellation is checked between
files and at roughly 1 MiB payload intervals. Closing the launcher requests
cancellation and joins the worker. An OS-blocked I/O call must return before the
worker can observe cancellation. Normal cancellation/failure removes staging
and never presents a partial file at the final destination.

A process crash can leave a clearly named `.partial` staging directory. It is not
a valid published backup and may be removed after the owning launcher exits.
Atomic publication does not promise durability against every power/filesystem
failure. Concurrent-library writers are tracked in #11; the export is a snapshot
of this instance's saved records, not a coordinated transaction with other
launcher instances or arbitrary external edits. Managed artwork is immutable
within the normal application workflow; size changes during copying are rejected.

## Verification

`mise run test` runs the Plum format checks and standalone backup integration.
A separate 64 MiB streaming fixture is enabled with `POWERLAUNCH_BACKUP_LARGE_MIB=64`;
Linux CI checks its normal-process RSS against a 32 MiB regression budget.
The integration independently opens/checks/extracts the output with Python's ZIP
reader, compares all metadata/artwork bytes, and verifies exclusions/deduplication.
It covers Unicode/spaced paths, empty libraries, missing/changed covers, cancelled
checking/review/writing/verification, injected mid-output failure, archive
corruption, destination races and worker shutdown. It preserves the source
library and all existing final backups.

`mise run memory-check` also runs this fixture with ASan and LSan without a GPU.
Linux real-input UI verification is:

```
xvfb-run -a -s '-screen 0 1600x1000x24' mise exec -- python3 tests/backup_ui.py
```

The UI check uses temporary data and verifies review-before-start, successful
publication, Escape cancellation and window close with a pending review. Reports
are kept in `build/backup-*.log` and `build/backup-memory.json`.

## Plum 0.0.41 workarounds

The task-exit file-read scratch leak is isolated in
[`plum-repros/file-read-task`](plum-repros/file-read-task/README.md). The owned
reader workaround releases its FILE and 64 KiB buffer together; fixtures assert
zero live readers after success, cancellation and failure, without LSan suppression.
A separate [`struct-field-order`](plum-repros/struct-field-order/README.md)
reproduction shows reordered struct literal fields causing a crash. Backup records
are constructed in declaration order and the idle/session UI path is tested.
Neither workaround modifies Plum or claims a language-wide ownership defect.
