"""Real keyboard/mouse backup review, export, cancellation and close protection."""
from pathlib import Path
import json
import os
import subprocess
import shutil
import sys
import tempfile
import time
import zipfile
from ui_driver import Driver, key, type_text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from profile_memory import seed_library, process_memory


def capture(driver, destination):
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'x11grab', '-video_size', '1280x820',
            '-i', os.environ['DISPLAY'] + f'+{driver.ox.value},{driver.oy.value}', '-frames:v', '1', '-y',
            str(destination)], timeout=10, check=True)

with tempfile.TemporaryDirectory(prefix='powerlaunch-backup-ui-') as folder:
    root = Path(folder)
    data = root / 'library'
    data.mkdir()
    seed_library(data, 5, covers=3)
    before = (data / 'library.json').read_bytes()
    env = os.environ.copy()
    env.update(POWERLAUNCH_DATA_DIR=str(data), POWERLAUNCH_MEMORY_REPORT='1')
    samples = []
    def sample(label):
        memory = process_memory(app.pid)
        if memory:
            samples.append({"checkpoint": label, **memory})

    with (ROOT / 'build/backup-ui.log').open('w') as log:
        app = subprocess.Popen([str(os.environ.get('POWERLAUNCH_TEST_EXE', ROOT / 'build/powerlaunch'))], env=env, stdout=log, stderr=log)
        try:
            driver = Driver()
            driver.click(90, 340)
            destination = root / 'backup.zip'
            driver.click(600, 303)
            type_text(str(destination))
            driver.click(300, 725)  # Review only; no final archive yet.
            time.sleep(0.4)
            assert not destination.exists()
            sample("review")
            capture(driver, ROOT / 'build/backup-review.png')
            driver.click(300, 725)  # Explicit Start backup.
            deadline = time.monotonic() + 10
            while not destination.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            assert destination.exists(), 'UI backup did not publish'
            with zipfile.ZipFile(destination) as archive:
                assert archive.testzip() is None
                assert json.loads(archive.read('library.json')) == json.loads(before)
                assert len(archive.namelist()) == 5  # manifest, library, 3 unique covers.
            time.sleep(0.1)
            sample("completed")
            capture(driver, ROOT / 'build/backup-complete.png')
            driver.click(600, 303)
            key(0xFF57)  # End, then remove old destination.
            for _ in str(destination):
                key(0xFF08)
            cancelled = root / 'cancelled.zip'
            type_text(str(cancelled))
            driver.click(300, 725)
            time.sleep(0.4)
            key(0xFF1B)  # Escape cancels the reviewed export; stays on backup screen.
            time.sleep(0.2)
            sample("cancelled")
            assert not cancelled.exists()
            assert not list(root.glob('.powerlaunch-backup-*'))
            driver.click(300, 725)  # Review again; closing must join/cancel it.
            time.sleep(0.4)
            driver.close()
            assert app.wait(timeout=10) == 0
            assert not cancelled.exists()
            assert not list(root.glob('.powerlaunch-backup-*'))
            assert (data / 'library.json').read_bytes() == before
        except Exception:
            print("Backup UI application status:", app.poll(), flush=True)
            if app.poll() is None:
                capture(driver, ROOT / 'build/backup-ui-failure.png')
            raise
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(timeout=5)
    (ROOT / 'build/backup-ui-memory.json').write_text(json.dumps({"samples": samples,
        "note": "OS checkpoints during a 5-game/3-cover UI export; these are not continuous peaks or proof of leak freedom."}, indent=2) + '\n')
    text = (ROOT / 'build/backup-ui.log').read_text()
    assert 'images_after_close=0' in text and 'textures_after_close=0' in text
print('Backup UI: review/start, independent ZIP check, Escape cancellation and pending-review window close passed.')
