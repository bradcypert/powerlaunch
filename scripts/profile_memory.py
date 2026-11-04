"""Sample application memory with standard OS APIs; no monitoring code in the UI.

Examples: python3 scripts/profile_memory.py --seconds 20 --games 2000
          python3 scripts/profile_memory.py --exe build/powerlaunch-before --seconds 20
Requires a display (or xvfb-run on Linux). Uses an isolated, generated library.
"""
from pathlib import Path
import argparse
import ctypes
import json
import hashlib
import os
import re
import subprocess
import sys
import struct
import tempfile
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]


def process_memory(pid):
    if os.name == "nt":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize",
                "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage"]]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        handle = kernel.OpenProcess(0x0400 | 0x0010, False, pid)
        if not handle:
            return None
        try:
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return None
            return {"rss_bytes": counters.WorkingSetSize, "private_bytes": counters.PrivateUsage,
                "anonymous_bytes": None}
        finally:
            kernel.CloseHandle(handle)
    if os.path.exists(f"/proc/{pid}/status"):
        try:
            values = dict(re.findall(r"^(VmRSS|VmHWM):\s*(\d+) kB", Path(f"/proc/{pid}/status").read_text(), re.M))
            private = None
            anonymous = None
            rollup = Path(f"/proc/{pid}/smaps_rollup")
            if rollup.exists():
                detail = rollup.read_text()
                private = sum(int(n) for n in re.findall(r"^Private_(?:Clean|Dirty):\s*(\d+) kB", detail, re.M)) * 1024
                match = re.search(r"^Anonymous:\s*(\d+) kB", detail, re.M)
                anonymous = int(match[1]) * 1024 if match else None
            return {"rss_bytes": int(values["VmRSS"]) * 1024, "private_bytes": private, "anonymous_bytes": anonymous}
        except (OSError, KeyError, ProcessLookupError):
            return None
    return None


def fixture_cover(index):
    """Deterministic test pixels, not production cover artwork."""
    width, height = 320, 480
    palettes = [(47, 69, 88), (103, 64, 69), (57, 84, 71), (72, 61, 105), (108, 83, 48)]
    color = palettes[index % len(palettes)]
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            stripe = 28 if (x + y + index * 23) // 48 % 3 == 0 else 0
            rows.extend((*[min(255, c + stripe) for c in color], 255))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


def seed_library(directory, count, covers=0):
    if covers:
        artwork = directory / "artwork"
        artwork.mkdir(exist_ok=True)
        for i in range(covers):
            (artwork / f"fixture-{i}.png").write_bytes(fixture_cover(i))
    games = [{"id": f"game-{i+1}", "title": f"Benchmark game {i+1:04d}", "target": str(ROOT / "missing-game"),
        "arguments": [], "working_directory": "", "cover": f"fixture-{i % covers}.png" if covers else "", "description": "A synthetic memory-test record.",
        "release_year": "1998", "developer": "Benchmark fixture", "tags": ["Adventure", "Test"],
        "favorite": i % 5 == 0} for i in range(count)]
    (directory / "library.json").write_text(json.dumps({"schema_version": 1, "next_id": str(count+1), "games": games}), encoding="utf-8")


def profile(exe, seconds, count, report, covers=0, base_env=None):
    with tempfile.TemporaryDirectory(prefix="powerlaunch-memory-") as temp:
        directory = Path(temp)
        seed_library(directory, count, covers)
        env = dict(base_env or os.environ)
        env.pop("POWERLAUNCH_SCREENSHOT", None)
        env.update(POWERLAUNCH_DATA_DIR=str(directory), POWERLAUNCH_SMOKE_FRAMES=str(max(1, round(seconds * 60))),
            PLUM_RT_STATS="1", POWERLAUNCH_MEMORY_REPORT="1")
        report.parent.mkdir(parents=True, exist_ok=True)
        log_path = report.with_suffix(".log")
        samples = []
        with log_path.open("w", encoding="utf-8") as log:
            app = subprocess.Popen([str(exe.resolve())], env=env, stdout=log, stderr=subprocess.STDOUT)
            start = time.monotonic()
            try:
                while app.poll() is None:
                    sample = process_memory(app.pid)
                    if sample:
                        samples.append({"seconds": round(time.monotonic() - start, 3), **sample})
                    if time.monotonic() - start > seconds * 4 + 30:
                        raise TimeoutError("Memory workload did not finish")
                    time.sleep(0.2)
                if app.returncode:
                    raise RuntimeError(f"Application exited {app.returncode}; see {log_path}")
            finally:
                if app.poll() is None:
                    app.kill()
                    app.wait()
        steady = [s for s in samples if s["seconds"] >= 3]
        if len(steady) < 5:
            raise RuntimeError("Not enough steady-state samples; use --seconds 10 or longer")
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        result = {"executable": str(exe), "binary_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
            "platform": sys.platform, "workload": "idle library", "games": count, "covers": covers,
            "private_metric": "private committed bytes" if os.name == "nt" else "resident private clean + dirty bytes",
            "graphics_renderer": next((line.strip() for line in log_text.splitlines() if "Renderer:" in line), "unknown"),
            "requested_seconds": seconds, "peak_rss_bytes": max(s["rss_bytes"] for s in samples),
            "steady_rss_growth_bytes": steady[-1]["rss_bytes"] - steady[0]["rss_bytes"],
            "steady_private_growth_bytes": (steady[-1]["private_bytes"] - steady[0]["private_bytes"])
                if all(s["private_bytes"] is not None for s in steady) else None,
            "steady_anonymous_growth_bytes": steady[-1]["anonymous_bytes"] - steady[0]["anonymous_bytes"]
                if all(s["anonymous_bytes"] is not None for s in steady) else None,
            "samples": samples, "runtime_allocation_stats": [line for line in log_text.splitlines() if "[plum-rt]" in line],
            "native_cache_stats": [line for line in log_text.splitlines() if "[powerlaunch-native]" in line],
            "interpretation": "Working set includes native libraries and the graphics driver. Allocation totals are cumulative, not live memory or proof of a leak."}
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k not in {"samples"}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=ROOT / "build" / ("powerlaunch.exe" if os.name == "nt" else "powerlaunch"))
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--games", type=int, default=2000)
    parser.add_argument("--covers", type=int, default=0)
    parser.add_argument("--report", type=Path, default=ROOT / "build/memory-profile.json")
    args = parser.parse_args()
    if args.seconds < 5 or args.games < 0 or args.covers < 0:
        parser.error("Use at least 5 seconds and a nonnegative game count")
    profile(args.exe, args.seconds, args.games, args.report, args.covers)
