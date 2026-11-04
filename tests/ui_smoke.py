"""Optional Linux/X11 integration test. Run in an isolated Xvfb display.

Exercises actual mouse/key events rather than a second implementation of the UI.
Requires libX11 and libXtst; writes only a temporary library and build screenshots.
"""
from pathlib import Path
import ctypes as C
import json
import os
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
x = C.CDLL("libX11.so.6")
t = C.CDLL("libXtst.so.6")
D, U, I = C.c_void_p, C.c_ulong, C.c_int
x.XOpenDisplay.argtypes, x.XOpenDisplay.restype = [C.c_char_p], D
x.XDefaultRootWindow.argtypes, x.XDefaultRootWindow.restype = [D], U
x.XQueryTree.argtypes = [D, U, C.POINTER(U), C.POINTER(U), C.POINTER(C.POINTER(U)), C.POINTER(C.c_uint)]
x.XFetchName.argtypes = [D, U, C.POINTER(C.c_char_p)]
x.XFree.argtypes = [D]
x.XFlush.argtypes = [D]
x.XSetInputFocus.argtypes = [D, U, I, U]
x.XKeysymToKeycode.argtypes, x.XKeysymToKeycode.restype = [D, U], C.c_ubyte
x.XkbKeycodeToKeysym.argtypes, x.XkbKeycodeToKeysym.restype = [D, C.c_ubyte, I, I], U
x.XTranslateCoordinates.argtypes = [D, U, U, I, I, C.POINTER(I), C.POINTER(I), C.POINTER(U)]
t.XTestFakeKeyEvent.argtypes = [D, C.c_uint, I, U]
t.XTestFakeButtonEvent.argtypes = [D, C.c_uint, I, U]
t.XTestFakeMotionEvent.argtypes = [D, I, I, I, U]
display = x.XOpenDisplay(None)
assert display, "Start this test inside xvfb-run"
root = x.XDefaultRootWindow(display)


def window():
    parent, base, children, count = U(), U(), C.POINTER(U)(), C.c_uint()
    x.XQueryTree(display, root, C.byref(base), C.byref(parent), C.byref(children), C.byref(count))
    found = None
    for i in range(count.value):
        name = C.c_char_p()
        if x.XFetchName(display, children[i], C.byref(name)) and name.value:
            if name.value == b"Powerlaunch":
                found = children[i]
            x.XFree(C.cast(name, D))
    if children:
        x.XFree(children)
    return found


def event_key(symbol, pressed):
    t.XTestFakeKeyEvent(display, x.XKeysymToKeycode(display, symbol), pressed, 0)
    x.XFlush(display)
    time.sleep(0.025)


def key(symbol):
    event_key(symbol, 1)
    event_key(symbol, 0)


def type_text(text):
    for char in text:
        symbol = ord(char)
        code = x.XKeysymToKeycode(display, symbol)
        shift = x.XkbKeycodeToKeysym(display, code, 0, 0) != symbol
        if shift:
            event_key(0xFFE1, 1)
        key(symbol)
        if shift:
            event_key(0xFFE1, 0)


with tempfile.TemporaryDirectory(prefix="powerlaunch-ui-") as directory:
    env = os.environ.copy()
    env["POWERLAUNCH_DATA_DIR"] = directory
    log = open(ROOT / "build/ui-smoke.log", "w")
    app = subprocess.Popen([str(ROOT / "build/powerlaunch")], env=env, stdout=log, stderr=log)
    try:
        deadline = time.monotonic() + 10
        target = None
        while not target and time.monotonic() < deadline:
            target = window()
            time.sleep(0.1)
        assert target, "Application did not open a window"
        time.sleep(0.4)
        x.XSetInputFocus(display, target, 2, 0)
        ox, oy, child = I(), I(), U()
        x.XTranslateCoordinates(display, target, root, 0, 0, C.byref(ox), C.byref(oy), C.byref(child))

        def click(px, py):
            t.XTestFakeMotionEvent(display, -1, ox.value + px, oy.value + py, 0)
            x.XFlush(display)
            time.sleep(0.05)
            t.XTestFakeButtonEvent(display, 1, 1, 0)
            x.XFlush(display)
            time.sleep(0.05)
            t.XTestFakeButtonEvent(display, 1, 0, 0)
            x.XFlush(display)
            time.sleep(0.1)

        click(960, 116)
        type_text("Test game")
        click(960, 184)
        type_text("/bin/true")
        click(960, 252)
        type_text("/tmp")
        click(960, 320)
        key(0xFF57)
        key(0xFF08)
        key(0xFF08)
        type_text('["two words", ""]')
        click(960, 524)
        type_text("Adventure, CD-ROM")
        click(960, 632)
        library = Path(directory) / "library.json"
        deadline = time.monotonic() + 3
        while not library.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert library.exists(), "Save changes did not create the library"
        saved = json.loads(library.read_text())
        assert saved["games"][0]["title"] == "Test game", saved
        assert saved["games"][0]["tags"] == ["Adventure", "CD-ROM"], saved
        assert saved["games"][0]["arguments"] == ["two words", ""], saved
        click(960, 116)
        key(0xFF57)  # End
        for _ in range(len("Test game")):
            key(0xFF08)  # Backspace
        type_text("Edited game")
        click(960, 632)
        time.sleep(0.2)
        assert json.loads(library.read_text())["games"][0]["title"] == "Edited game"
        click(1160, 632)  # Play a real harmless executable.
        assert app.poll() is None, "Launching closed the launcher"
    finally:
        app.terminate()
        app.wait(timeout=5)
        log.close()
    env.update(POWERLAUNCH_SMOKE_FRAMES="3", POWERLAUNCH_SCREENSHOT=str(ROOT / "build/library-smoke.png"))
    subprocess.run([str(ROOT / "build/powerlaunch")], env=env, stdout=subprocess.DEVNULL, check=True)
    assert json.loads(library.read_text())["games"][0]["title"] == "Edited game"
    print("UI integration: register, edit, save, tags, launch, and reload passed.")
