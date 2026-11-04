"""Open and close the packaged window with build-tool directories off PATH."""
from pathlib import Path
import argparse
import filecmp
import os
import shutil
import subprocess
import tempfile
from package_windows import imports, runtime_dependencies

ROOT = Path(__file__).resolve().parents[1]


def software_renderer(package, destination, runtime, system):
    """Keep the downloaded bundle untouched; add Mesa only to a test copy."""
    renderer = runtime / "opengl32.dll"
    objdump = runtime / "objdump.exe"
    if not renderer.is_file():
        raise SystemExit("Install mingw-w64-ucrt-x86_64-mesa for the CI software-rendering check.")
    dependencies = runtime_dependencies(renderer, runtime, system,
        lambda binary: imports(binary, objdump))
    shutil.copytree(package, destination)
    for source in [renderer, *dependencies]:
        target = destination / source.name
        if target.exists():
            if not filecmp.cmp(source, target, shallow=False):
                raise SystemExit(f"CI renderer would replace a different packaged DLL: {source.name}")
        else:
            shutil.copy2(source, target)
    return destination


def smoke(use_software=False, memory_seconds=0):
    if os.name != "nt":
        raise SystemExit("The packaged Windows smoke test must run on Windows.")
    package = ROOT / "build/package/powerlaunch-windows-x64"
    with tempfile.TemporaryDirectory(prefix="Powerlaunch packaged smoke ") as directory:
        env = os.environ.copy()
        windows = Path(env["WINDIR"])
        if use_software:
            prefix = Path(subprocess.check_output(
                ["pkg-config", "--variable=prefix", "raylib"], text=True).strip())
            package = software_renderer(package, Path(directory) / "app", prefix / "bin", windows / "System32")
            env["LIBGL_ALWAYS_SOFTWARE"] = "true"
            env["GALLIUM_DRIVER"] = "llvmpipe"
        env["PATH"] = os.pathsep.join([str(windows / "System32"), str(windows)])
        env["POWERLAUNCH_DATA_DIR"] = directory
        env["POWERLAUNCH_SMOKE_FRAMES"] = "5"
        screenshot = ROOT / "build/windows-smoke.png"
        screenshot.unlink(missing_ok=True)
        env["POWERLAUNCH_SCREENSHOT"] = str(screenshot)
        log_path = ROOT / "build/windows-smoke.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run([str(package / "powerlaunch.exe")], cwd=directory,
                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=45)
        if result.returncode != 0:
            print(log_path.read_text(encoding="utf-8", errors="replace"))
            raise SystemExit(f"Packaged application failed with exit code {result.returncode}; see windows-smoke.log")
        if not screenshot.is_file() or screenshot.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit("Packaged application did not render its expected screenshot.")
        if use_software and "llvmpipe" not in log_path.read_text(encoding="utf-8", errors="replace").lower():
            raise SystemExit("The CI window did not report the requested llvmpipe renderer.")
        print("Packaged window rendered and exited without build tools or MSYS2 on PATH."
            + (" CI-only Mesa DLLs were added to a disposable test copy." if use_software else ""))
        if memory_seconds:
            from profile_memory import profile
            profile(package / "powerlaunch.exe", memory_seconds, 2000,
                ROOT / "build/windows-memory.json", base_env=env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--software-rendering", action="store_true",
        help="Add Mesa to a disposable copy for hosted runners without GPU drivers")
    parser.add_argument("--memory-seconds", type=int, default=0)
    args = parser.parse_args()
    smoke(args.software_rendering, args.memory_seconds)
