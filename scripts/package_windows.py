"""Bundle PE runtime dependencies, recursively, without copying Windows DLLs.

Run using the UCRT64 Python after `mise run build`. The artifact uploader creates
the downloadable ZIP from the resulting folder. No developer tools are bundled.
"""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import struct
import tomllib

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "build/package/powerlaunch-windows-x64"


def imports(binary, objdump):
    output = subprocess.check_output([str(objdump), "-p", str(binary)], text=True)
    return re.findall(r"^\s*DLL Name:\s*(\S+)\s*$", output, re.MULTILINE)


def file_index(directory):
    return {path.name.casefold(): path for path in directory.iterdir() if path.is_file()}


def verify_app_icon(executable):
    """Check the actual linked PE, so a missing resource object cannot go unnoticed."""
    data = executable.read_bytes()
    try:
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        if data[:2] != b'MZ' or data[pe:pe+4] != b'PE\0\0':
            raise ValueError('not a PE executable')
        optional = pe + 24
        if struct.unpack_from('<H', data, optional)[0] != 0x20b:
            raise ValueError('expected a Windows x64 PE32+ executable')
        resource_rva = struct.unpack_from('<I', data, optional + 112 + 2*8)[0]
        sections = optional + struct.unpack_from('<H', data, pe + 20)[0]
        root = None
        for i in range(struct.unpack_from('<H', data, pe + 6)[0]):
            virtual_size, virtual, raw_size, raw = struct.unpack_from('<IIII', data, sections + i*40 + 8)
            if virtual <= resource_rva < virtual + max(virtual_size, raw_size):
                root = raw + resource_rva - virtual
                break
        if root is None:
            raise ValueError('no resource directory')
        named, numbered = struct.unpack_from('<HH', data, root + 12)
        types = {struct.unpack_from('<I', data, root + 16 + i*8)[0] for i in range(named + numbered)}
        if not {3, 14}.issubset(types):
            raise ValueError('missing icon images or icon group')
    except (ValueError, struct.error) as error:
        raise SystemExit(f'The Windows app icon was not embedded: {error}')
    print('Verified icon images and icon group in the linked Windows executable.')


def runtime_dependencies(executable, runtime_directory, system_directory, inspect):
    """Follow transitive imports; refuse a package with any unresolved dependency."""
    runtime = file_index(runtime_directory)
    system = file_index(system_directory)
    adjacent = file_index(executable.parent)
    pending = [executable]
    visited = {executable.name.casefold()}
    bundled = {}
    while pending:
        binary = pending.pop()
        for name in inspect(binary):
            key = name.casefold()
            if key in visited:
                continue
            visited.add(key)
            if key.startswith(("api-ms-win-", "ext-ms-win-")) or key in system:
                continue
            dependency = adjacent.get(key) or runtime.get(key)
            if dependency is None:
                raise RuntimeError(f"Unresolved runtime DLL {name!r}, imported by {binary.name}")
            bundled[key] = dependency
            pending.append(dependency)
    return sorted(bundled.values(), key=lambda path: path.name.casefold())


def package():
    if os.name != "nt":
        raise SystemExit("Windows packaging must run on Windows in the MSYS2 UCRT64 environment.")
    executable = ROOT / "build/powerlaunch.exe"
    if not executable.is_file():
        raise SystemExit("Build powerlaunch.exe with mise run build first.")
    verify_app_icon(executable)
    prefix = Path(subprocess.check_output(
        ["pkg-config", "--variable=prefix", "raylib"], text=True).strip())
    runtime = prefix / "bin"
    objdump = runtime / "objdump.exe"
    if not objdump.is_file():
        raise SystemExit("Install mingw-w64-ucrt-x86_64-binutils before packaging.")
    system = Path(os.environ["WINDIR"]) / "System32"
    dependencies = runtime_dependencies(executable, runtime, system,
        lambda binary: imports(binary, objdump))
    licenses = prefix / "share/licenses"
    if not licenses.is_dir():
        raise SystemExit("MSYS2 dependency license files were not found; refusing to omit them.")

    # Only replace this script's generated output, never the build or user data.
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    DESTINATION.mkdir(parents=True)
    for source in [executable, *dependencies]:
        shutil.copy2(source, DESTINATION / source.name)
    shutil.copytree(licenses, DESTINATION / "licenses/msys2")
    vendored = DESTINATION / "licenses/vendored"
    vendored.mkdir(parents=True)
    for name in ["raygui.h", "tinyfiledialogs.h", "README.md"]:
        shutil.copy2(ROOT / "app/vendor" / name, vendored / name)
    (DESTINATION / "README.txt").write_text(
        "Powerlaunch for Windows x64 — development build\n\n"
        "Extract the entire ZIP to one folder, then run powerlaunch.exe.\n"
        "Keep the bundled DLL files beside the executable.\n"
        "Plum, Clang, Python, Mise, and MSYS2 are not needed to run this build.\n\n"
        "Your library is stored in %LOCALAPPDATA%/Powerlaunch.\n"
        "This is an unsigned prototype; backup/restore and other features are unfinished.\n"
        "Source and issues: https://github.com/bradcypert/powerlaunch\n\n"
        "Third-party license notices are in the licenses folder. The MSYS2 notices\n"
        "include the build environment's license collection so transitive DLL\n"
        "dependencies retain their notices.\n", encoding="utf-8")
    with (ROOT / "mise.toml").open("rb") as config:
        plum = tomllib.load(config)["tools"]["github:bradcypert/plum"]
    manifest = {
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "plum": plum,
        "raylib": subprocess.check_output(["pkg-config", "--modversion", "raylib"], text=True).strip(),
        "runtime_dlls": [path.name for path in dependencies],
    }
    (DESTINATION / "build-info.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {executable.name} and {len(dependencies)} runtime DLLs in {DESTINATION}")


if __name__ == "__main__":
    package()
