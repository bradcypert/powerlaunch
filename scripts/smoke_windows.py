"""Open and close the packaged window with build-tool directories off PATH."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def smoke():
    if os.name != "nt":
        raise SystemExit("The packaged Windows smoke test must run on Windows.")
    package = ROOT / "build/package/powerlaunch-windows-x64"
    with tempfile.TemporaryDirectory(prefix="Powerlaunch packaged smoke ") as directory:
        env = os.environ.copy()
        windows = Path(env["WINDIR"])
        env["PATH"] = os.pathsep.join([str(windows / "System32"), str(windows)])
        env["POWERLAUNCH_DATA_DIR"] = directory
        env["POWERLAUNCH_SMOKE_FRAMES"] = "5"
        screenshot = ROOT / "build/windows-smoke.png"
        screenshot.unlink(missing_ok=True)
        env["POWERLAUNCH_SCREENSHOT"] = str(screenshot)
        with (ROOT / "build/windows-smoke.log").open("w", encoding="utf-8") as log:
            result = subprocess.run([str(package / "powerlaunch.exe")], cwd=directory,
                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=45)
        if result.returncode != 0:
            raise SystemExit(f"Packaged application failed with exit code {result.returncode}; see windows-smoke.log")
        if not screenshot.is_file() or screenshot.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit("Packaged application did not render its expected screenshot.")
        print("Packaged window rendered and exited without build tools or MSYS2 on PATH.")


if __name__ == "__main__":
    smoke()
