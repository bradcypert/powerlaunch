"""Real child survival, literal argv, working-directory and launch-error checks."""
from pathlib import Path
import os
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
suffix = ".exe" if os.name == "nt" else ""
with tempfile.TemporaryDirectory(prefix="powerlaunch process Café ") as directory:
    tmp = Path(directory)
    helper = tmp / f"game helper Café{suffix}"
    driver = tmp / f"launcher{suffix}"
    helper_command = ["clang", str(ROOT / "tests/process_helper.c"), "-o", str(helper)]
    if os.name == "nt":
        helper_command += ["-lshell32"]
    subprocess.run(helper_command, check=True)
    command = ["clang", "-Wall", "-Wextra", "-Werror", str(ROOT / "tests/process_driver.c"),
               str(ROOT / "app/native/process.c"), "-o", str(driver)]
    if os.name == "nt":
        command += ["-lole32", "-lshell32"]
    subprocess.run(command, check=True)
    cwd = tmp / "working directory Café"
    cwd.mkdir()
    output = tmp / "result.txt"
    args = ["", "two words", 'a"quote', "trailing\\", "$(touch NEVER);literal", "Café"]
    original = Path.cwd()
    subprocess.run([str(driver), str(helper), str(cwd), str(output), *args], check=True)
    # The driver is gone; the game must still be alive and complete its work.
    deadline = time.monotonic() + 5
    lines = []
    while time.monotonic() < deadline:
        if output.exists():
            lines = output.read_text(encoding="utf-8").splitlines()
            if len(lines) == len(args) + 1:
                break
        time.sleep(0.05)
    assert output.exists(), "Game did not survive launcher exit"
    assert Path(lines[0]).resolve() == cwd.resolve(), lines
    assert lines[1:] == args, lines
    assert Path.cwd() == original
    missing = subprocess.run([str(driver), str(tmp / "missing.exe"), str(cwd)], capture_output=True, text=True)
    assert missing.returncode == 1 and missing.stderr.strip(), missing
    invalid_cwd = subprocess.run([str(driver), str(helper), str(tmp / "missing directory")], capture_output=True, text=True)
    assert invalid_cwd.returncode == 1 and invalid_cwd.stderr.strip(), invalid_cwd
    assert not (original / "NEVER").exists()
    print("Process integration: child survival, cwd, literal argv, and launch errors passed.")
