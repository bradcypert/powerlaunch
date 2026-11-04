"""Leak/invalid-access check of Plum application ownership, independent of GPU."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != "linux":
    raise SystemExit("AddressSanitizer/LeakSanitizer validation currently runs on Linux.")
env = os.environ.copy()
env["POWERLAUNCH_SANITIZE"] = "1"
subprocess.run([sys.executable, "scripts/build.py"], cwd=ROOT, env=env, check=True)
env.update(POWERLAUNCH_HEADLESS_MEMORY_CYCLES="250", PLUM_RT_STATS="1",
    ASAN_OPTIONS="detect_leaks=1:halt_on_error=1", LSAN_OPTIONS="exitcode=23")
log = ROOT / "build/memory-sanitizer.log"
with log.open("w", encoding="utf-8") as stream:
    result = subprocess.run([str(ROOT / "build/powerlaunch-asan")], cwd=ROOT,
        env=env, stdout=stream, stderr=subprocess.STDOUT)
print(log.read_text(encoding="utf-8", errors="replace"))
if result.returncode:
    raise SystemExit(result.returncode)
print("Graphics-free address/leak sanitizer workload passed.")
