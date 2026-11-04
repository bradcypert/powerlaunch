"""Repeated real UI navigation + cover-cache churn, with OS memory checkpoints."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from ui_driver import Driver, key

ROOT = Path(__file__).resolve().parents[1]
cycles = int(os.environ.get("POWERLAUNCH_MEMORY_UI_CYCLES", "4"))
assert 2 <= cycles <= 64
sys.path.insert(0, str(ROOT / "scripts"))
from profile_memory import process_memory, seed_library

with tempfile.TemporaryDirectory(prefix="powerlaunch-ui-memory-") as folder:
    directory = Path(folder)
    seed_library(directory, 2000, covers=40)
    env = os.environ.copy()
    env.update(POWERLAUNCH_DATA_DIR=folder, PLUM_RT_STATS="1", POWERLAUNCH_MEMORY_REPORT="1")
    log_path = ROOT / "build/memory-interactions.log"
    samples = []
    with log_path.open("w", encoding="utf-8") as log:
        app = subprocess.Popen([str(ROOT / "build/powerlaunch")], env=env, stdout=log, stderr=log)
        start = time.monotonic()
        try:
            driver = Driver()
            for cycle in range(cycles):
                # Revisit the same working set after warming the bounded cache.
                driver.move(600, 360)
                for step in range(12):
                    driver.scroll(4)
                    time.sleep(0.06)
                    memory = process_memory(app.pid)
                    if memory:
                        samples.append({"cycle": cycle, "seconds": round(time.monotonic()-start, 2), **memory})
                driver.scroll(-48)
                time.sleep(0.15)
                driver.click(280, 260)
                driver.click(710, 264)  # Detail -> edit.
                key(0xFF1B)  # Escape -> unchanged detail.
                key(0xFF1B)  # Escape -> library.
            driver.close()
            if app.wait(timeout=5) != 0:
                raise RuntimeError("Application failed during repeated UI navigation")
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(timeout=5)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    stats = re.search(r"peak_textures=(\d+) peak_texture_bytes=(\d+) textures_after_close=(\d+)", text)
    assert stats, "Native cache diagnostics were not emitted"
    assert int(stats[1]) <= 24 and int(stats[1]) >= 20, stats[0]
    assert int(stats[3]) == 0, stats[0]
    warm = [s for s in samples if s["cycle"] >= 1]
    assert warm
    report = {"workload": f"{cycles} repeated scroll/detail/edit/back cycles, 2000 games, 40 covers",
        "peak_rss_bytes": max(s["rss_bytes"] for s in samples),
        "post_warmup_rss_growth_bytes": warm[-1]["rss_bytes"]-warm[0]["rss_bytes"],
        "post_warmup_private_growth_bytes": warm[-1]["private_bytes"]-warm[0]["private_bytes"],
        "post_warmup_anonymous_growth_bytes": warm[-1]["anonymous_bytes"]-warm[0]["anonymous_bytes"],
        "native_cache": stats[0], "samples": samples,
        "interpretation": "A short regression workload, not a proof of leak freedom. Cache bytes are app-owned texture sizes, not total driver/GPU memory."}
    (ROOT / "build/memory-interactions.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k != "samples"}, indent=2))
