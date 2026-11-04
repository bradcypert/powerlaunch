"""Real input integration: browse/detail/edit, arguments, unsaved close and launch."""
from pathlib import Path
import json
import os
import shlex
import subprocess
import tempfile
import time
from ui_driver import Driver, key, type_text, cursor_image

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="powerlaunch-ui-") as directory:
    env = os.environ.copy()
    env.update(POWERLAUNCH_DATA_DIR=directory, POWERLAUNCH_MEMORY_REPORT="1", PLUM_RT_STATS="1")
    marker = Path(directory) / "launched"
    fixture = Path(directory) / "fixture-game.sh"
    fixture.write_text("#!/bin/sh\nprintf started > " + shlex.quote(str(marker)) + "\n")
    fixture.chmod(0o700)
    log = open(ROOT / "build/ui-smoke.log", "w")
    app = subprocess.Popen([str(ROOT / "build/powerlaunch")], env=env, stdout=log, stderr=log)
    library = Path(directory) / "library.json"
    try:
        driver = Driver()
        def cursor_at(px, py):
            driver.move(px, py)
            time.sleep(0.12)
            return cursor_image()

        arrow = cursor_at(200, 80)
        hand = cursor_at(90, 286)
        assert hand != arrow, "Buttons should display a pointing cursor"
        assert cursor_at(200, 80) == arrow, "Leaving a button should restore the arrow"
        driver.click(90, 286)  # Add game, separate editor.
        ibeam = cursor_at(600, 142)
        assert ibeam != arrow and ibeam != hand, "Editable fields should display an I-beam"
        driver.click(600, 142)
        type_text("Test game")
        driver.click(90, 155)  # Invalid draft must survive a failed save from confirmation.
        assert cursor_at(90, 286) == arrow, "Modal background buttons must not request a pointer"
        driver.click(470, 467)  # Save fails because a target has not been chosen.
        assert not library.exists(), "Invalid draft should not be committed"
        driver.click(812, 467)  # Keep editing after failed save.
        driver.click(600, 220)
        type_text(str(fixture))
        driver.click(600, 536)
        type_text("/tmp")
        driver.click(600, 458)
        type_text("Adventure, CD-ROM")
        driver.click(560, 658)  # Add first argument.
        driver.click(560, 658)
        type_text("two words")
        driver.click(560, 710)  # Add empty second argument.
        driver.click(1170, 48)  # Save -> detail view.
        time.sleep(0.2)
        assert library.exists(), "Save changes did not create the library"
        saved = json.loads(library.read_text())
        assert saved["games"][0]["title"] == "Test game", saved
        assert saved["games"][0]["tags"] == ["Adventure", "CD-ROM"], saved
        assert saved["games"][0]["arguments"] == ["two words", ""], saved
        driver.click(280, 46)  # Back to the library.
        assert cursor_at(300, 230) == hand, "Library cards should display a pointing cursor"
        driver.click(300, 120)
        driver.click(300, 209)  # Explicit Adventure tag option.
        driver.click(1160, 120)
        driver.click(1100, 209)  # Explicit Z-to-A sort option.
        key(0xFF09)  # Tab from sort control to the grid.
        key(0xFF0D)  # Enter opens the selected game.
        time.sleep(0.1)
        assert not marker.exists(), "Enter should open details without also launching"
        driver.click(710, 264)  # Edit game.
        driver.click(600, 142)
        key(0xFF57)
        for _ in range(len("Test game")):
            key(0xFF08)
        type_text("Edited game")
        driver.click(90, 155)  # Leaving editor must ask about unsaved changes.
        driver.click(812, 467)  # Keep editing.
        assert json.loads(library.read_text())["games"][0]["title"] == "Test game"
        driver.chord(ord('s'))
        time.sleep(0.2)
        assert json.loads(library.read_text())["games"][0]["title"] == "Edited game"
        driver.click(560, 264)  # Play a harmless real executable.
        assert app.poll() is None, "Launching closed the launcher"
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists(), "The Play action did not launch the test game"
        driver.click(710, 264)
        driver.click(600, 302)
        type_text("Changed description")
        driver.close()  # WM close must preserve a dirty editor.
        assert app.poll() is None, "Window close silently discarded unsaved edits"
        driver.click(812, 467)
        driver.chord(ord('s'))
        time.sleep(0.2)
        assert json.loads(library.read_text())["games"][0]["description"] == "Changed description"
        driver.close()  # Clean close must now work.
        assert app.wait(timeout=5) == 0
    finally:
        if app.poll() is None:
            app.terminate()
            app.wait(timeout=5)
        log.close()
    env.update(POWERLAUNCH_SMOKE_FRAMES="4", POWERLAUNCH_SCREENSHOT=str(ROOT / "build/library-smoke.png"))
    subprocess.run([str(ROOT / "build/powerlaunch")], env=env, stdout=subprocess.DEVNULL, check=True)
    assert json.loads(library.read_text())["games"][0]["title"] == "Edited game"
    print("UI integration: registration, detail/edit, argument rows, tags, launch, unsaved navigation/close, and reload passed.")
