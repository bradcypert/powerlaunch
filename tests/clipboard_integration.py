"""PNG conversion/ownership plus actual CF_DIB clipboard integration on Windows."""
from pathlib import Path
import os
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    if sys.platform == "darwin":
        print("Clipboard image integration skipped: the selected raylib macOS backend does not implement image paste.")
        raise SystemExit(0)
    system_clipboard = os.name == "nt" and (os.environ.get("CI") == "true" or os.environ.get("POWERLAUNCH_TEST_SYSTEM_CLIPBOARD") == "1")
    with tempfile.TemporaryDirectory(prefix="powerlaunch-clipboard-") as directory:
        output = Path(directory) / ("clipboard.exe" if os.name == "nt" else "clipboard")
        command = ["clang", "-Wall", "-Wextra", "-Werror", "tests/clipboard_driver.c", "app/native/clipboard.c"]
        if system_clipboard:
            command += ["tests/clipboard_windows.c", "-luser32"]
        else:
            command += ["-DPOWERLAUNCH_FAKE_CLIPBOARD"]
        if os.environ.get("POWERLAUNCH_SANITIZE") == "1":
            command += ["-fsanitize=address", "-fno-omit-frame-pointer"]
        command += shlex.split(subprocess.check_output(["pkg-config", "--cflags", "--libs", "raylib"], text=True))
        command += ["-o", str(output)]
        subprocess.run(command, cwd=ROOT, check=True)
        subprocess.run([str(output)], cwd=ROOT, check=True, timeout=30)
    print("Clipboard integration: empty/text clipboard and 50 PNG capture/decode/release cycles passed."
          + (" Read actual Windows CF_DIB data." if system_clipboard else " Getter injected; real X11 paste is covered by UI tests."))
