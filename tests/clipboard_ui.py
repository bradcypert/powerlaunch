"""Real X11 clipboard -> editor draft -> managed PNG and game-folder copy."""
from pathlib import Path
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
from ui_driver import Driver, type_text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from profile_memory import fixture_cover

with tempfile.TemporaryDirectory(prefix="powerlaunch-clipboard-ui-") as folder:
    root = Path(folder)
    game = root / "game"
    game.mkdir()
    target = game / "game.sh"
    target.write_text("#!/bin/sh\nexit 0\n")
    source = root / "copied-image.png"
    source.write_bytes(fixture_cover(0))
    existing = game / "powerlaunch_cover.png"
    existing.write_bytes(b"existing user cover")
    env = os.environ.copy()
    env.update(POWERLAUNCH_DATA_DIR=str(root / "library"), POWERLAUNCH_MEMORY_REPORT="1")
    log_path = ROOT / "build/clipboard-ui.log"
    provider = None

    def clipboard(path, mime):
        global provider
        if provider and provider.poll() is None:
            provider.terminate()
            provider.wait(timeout=3)
        provider = subprocess.Popen(["xclip", "-selection", "clipboard", "-target", mime,
            "-in", "-quiet", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.15)

    def drafts():
        return list((root / "library/drafts").glob("*.png"))

    with log_path.open("w") as log:
        app = subprocess.Popen([str(ROOT / "build/powerlaunch")], env=env, stdout=log, stderr=log)
        try:
            driver = Driver()
            driver.click(90, 286)
            clipboard(source, "image/png")
            driver.click(330, 518)  # Paste without needing title/target first.
            time.sleep(0.25)
            assert len(drafts()) == 1, "Pasting did not stage a clipboard PNG; see clipboard-ui.log"
            first = drafts()[0]
            assert struct.unpack(">II", first.read_bytes()[16:24]) == (320, 480)
            assert list(game.glob("powerlaunch_cover*.png")) == [existing], "Paste wrote game files before Save"
            # Replacing a paste removes the prior temporary, not the user file.
            driver.click(300, 220)
            driver.chord(ord('v'))
            time.sleep(0.2)
            assert len(drafts()) == 1 and drafts()[0] != first
            assert not first.exists()
            # Pasting clipboard text leaves the current cover intact.
            current = drafts()[0]
            text = root / "text.txt"
            text.write_text("normal text")
            clipboard(text, "UTF8_STRING")
            driver.click(330, 518)
            assert drafts() == [current]
            # Text fields keep Ctrl+V behavior and don't replace the cover.
            driver.click(600, 142)
            driver.chord(ord('v'))
            assert drafts() == [current]
            clipboard(source, "image/png")
            driver.click(600, 220)
            type_text(str(target))
            driver.click(1170, 48)
            time.sleep(0.25)
            library = root / "library/library.json"
            saved = json.loads(library.read_text())
            assert saved["games"][0]["title"] == "normal text", saved
            managed = root / "library/artwork" / saved["games"][0]["cover"]
            exported = game / "powerlaunch_cover-2.png"
            assert exported.read_bytes() == managed.read_bytes()
            assert existing.read_bytes() == b"existing user cover"
            assert drafts() == [], "Successful save leaked a draft PNG"
            driver.click(710, 264)
            driver.click(330, 518)
            assert len(drafts()) == 1
            driver.click(1030, 48)  # Cancel -> ask about dirty artwork.
            driver.click(630, 467)  # Discard.
            assert drafts() == [], "Discard leaked a draft PNG"
            assert not (game / "powerlaunch_cover-3.png").exists()
            assert json.loads(library.read_text()) == saved
            driver.close()
            assert app.wait(timeout=5) == 0
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(timeout=5)
            if provider and provider.poll() is None:
                provider.terminate()
                provider.wait(timeout=3)
    print("Clipboard UI: image paste, focused Ctrl+V, text paste, replacement/discard cleanup, collision-safe game copy, managed copy and metadata passed.")
