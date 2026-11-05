"""PNG conversion/ownership plus actual CF_DIB clipboard integration on Windows."""
from pathlib import Path
import os
import shlex
import shutil
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
        if sys.platform == "linux" and os.environ.get("POWERLAUNCH_SANITIZE") == "1":
            # Exercise the actual Plum handle -> borrowed pointer -> Bytes copy,
            # independent of clipboard/display availability and GPU allocations.
            sys.path.insert(0, str(ROOT / "scripts"))
            from build import PLUM, environment
            project = Path(directory) / "plum-copy"
            (project / "native").mkdir(parents=True)
            (project / "clipboard").mkdir()
            shutil.copy2(ROOT / "app/clipboard/image.plum", project / "clipboard/image.plum")
            shutil.copy2(ROOT / "app/native/clipboard.c", project / "native/clipboard.c")
            shutil.copy2(ROOT / "tests/clipboard_image_fixture.c", project / "native/fixture.c")
            shutil.copy2(ROOT / "tests/clipboard_ownership.plum", project / "main.plum")
            (project / "plum.pkg").write_text('Package { name: "clipboard-copy-test", native_deps: [] }\n')
            env, options = environment()
            helper = project / "check"
            subprocess.run([PLUM, "build", str(project), "-o", str(helper), *options], cwd=ROOT, env=env, check=True)
            subprocess.run([str(helper)], cwd=ROOT, env=env, check=True, timeout=30)
    print("Clipboard integration: empty/text clipboard and 50 PNG capture/decode/release cycles passed."
          + (" Read actual Windows CF_DIB data." if system_clipboard else " Getter injected; real X11 paste is covered by UI tests."))
