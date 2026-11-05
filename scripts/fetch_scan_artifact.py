"""Fetch an existing CI artifact, verify its identity, inventory, then extract.

Never executes package contents. gh supplies repository-scoped authentication.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile

REPOSITORY = "bradcypert/powerlaunch"


def extract_verified(archive, metadata, run_id, expected_exe_sha256, destination, report):
    if metadata.get("expired") or metadata.get("name") != "powerlaunch-windows-x64":
        raise ValueError("Expected an unexpired powerlaunch-windows-x64 artifact")
    if metadata.get("workflow_run", {}).get("id") != run_id:
        raise ValueError("Artifact does not belong to the requested workflow run")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_exe_sha256):
        raise ValueError("Expected executable SHA-256 must contain 64 hex digits")
    digest = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
    if metadata.get("digest") != digest:
        raise ValueError("Downloaded archive does not match GitHub's artifact digest")
    if destination.exists():
        raise ValueError("Extraction destination must be new")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if sum(e.file_size for e in entries) > 256 * 1024 * 1024:
            raise ValueError("Artifact exceeds the investigation's uncompressed size limit")
        seen = set()
        files = []
        for entry in entries:
            # ZipInfo normalizes backslashes on Windows and truncates at NUL.
            # Reject altered names using the original header spelling too.
            original = entry.orig_filename
            path = PurePosixPath(original)
            key = entry.filename.casefold()
            if (original != entry.filename or path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                    or ":" in entry.filename or key in seen
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError("Unexpected archive path: " + entry.filename)
            seen.add(key)
            if entry.is_dir():
                continue
            if entry.file_size > 64 * 1024 * 1024:
                raise ValueError("Artifact member exceeds the investigation's file limit")
            data = package.read(entry)
            files.append({"path": entry.filename, "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest()})
        executable = next((f for f in files if f["path"] == "powerlaunch.exe"), None)
        if executable is None or executable["sha256"] != expected_exe_sha256.lower():
            raise ValueError("Executable differs from the expected CI-recorded SHA-256")
        evidence = {"repository": REPOSITORY, "run_id": run_id,
            "artifact_id": metadata["id"], "archive_digest": digest,
            "source_commit": metadata["workflow_run"].get("head_sha"), "files": files}
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        # Inventory is retained even if real-time protection quarantines a file
        # during extraction. Treat that as incomplete evidence, never a clean scan.
        destination.mkdir(parents=True)
        package.extractall(destination)
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--expected-exe-sha256", required=True)
    parser.add_argument("--root", type=Path, default=Path("build/defender-investigation"))
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    endpoint = f"/repos/{REPOSITORY}/actions/artifacts/{args.artifact_id}"
    metadata = json.loads(subprocess.check_output(["gh", "api", endpoint], text=True))
    (args.root / "artifact.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    archive = args.root / "artifact.zip"
    with archive.open("wb") as stream:
        subprocess.run(["gh", "api", endpoint + "/zip"], stdout=stream, check=True)
    evidence = extract_verified(archive, metadata, args.run_id, args.expected_exe_sha256,
        args.root / "package", args.root / "reports/inventory.json")
    print(json.dumps({key: evidence[key] for key in evidence if key != "files"}, indent=2))
