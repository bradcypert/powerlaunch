"""Shared real-input X11 driver for the UI and memory integration checks."""
from pathlib import Path
import ctypes as C
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



x.XInternAtom.argtypes, x.XInternAtom.restype = [D, C.c_char_p, I], U
x.XSendEvent.argtypes = [D, U, I, C.c_long, D]

class ClientMessage(C.Structure):
    _fields_ = [("type", I), ("serial", U), ("send_event", I), ("display", D),
        ("window", U), ("message_type", U), ("format", I), ("data", C.c_long * 5)]

class Driver:
    def __init__(self):
        deadline = time.monotonic() + 10
        self.target = None
        while not self.target and time.monotonic() < deadline:
            self.target = window()
            time.sleep(0.05)
        assert self.target, "Application did not open a window"
        time.sleep(0.25)
        x.XSetInputFocus(display, self.target, 2, 0)
        self.ox, self.oy, child = I(), I(), U()
        x.XTranslateCoordinates(display, self.target, root, 0, 0, C.byref(self.ox), C.byref(self.oy), C.byref(child))

    def move(self, px, py):
        t.XTestFakeMotionEvent(display, -1, self.ox.value + px, self.oy.value + py, 0)
        x.XFlush(display)

    def click(self, px, py):
        self.move(px, py)
        time.sleep(0.04)
        t.XTestFakeButtonEvent(display, 1, 1, 0)
        x.XFlush(display)
        time.sleep(0.04)
        t.XTestFakeButtonEvent(display, 1, 0, 0)
        x.XFlush(display)
        time.sleep(0.09)

    def scroll(self, amount):
        for _ in range(abs(amount)):
            t.XTestFakeButtonEvent(display, 5 if amount > 0 else 4, 1, 0)
            t.XTestFakeButtonEvent(display, 5 if amount > 0 else 4, 0, 0)
            x.XFlush(display)
            time.sleep(0.02)

    def close(self):
        event = ClientMessage()
        event.type, event.display, event.window, event.format = 33, display, self.target, 32
        event.message_type = x.XInternAtom(display, b"WM_PROTOCOLS", False)
        event.data[0] = x.XInternAtom(display, b"WM_DELETE_WINDOW", False)
        x.XSendEvent(display, self.target, False, 0, C.byref(event))
        x.XFlush(display)
        time.sleep(0.15)

    def chord(self, symbol):
        event_key(0xFFE3, 1)
        key(symbol)
        event_key(0xFFE3, 0)


class CursorImage(C.Structure):
    _fields_ = [("x", C.c_short), ("y", C.c_short),
        ("width", C.c_ushort), ("height", C.c_ushort),
        ("xhot", C.c_ushort), ("yhot", C.c_ushort),
        ("serial", U), ("pixels", C.POINTER(U))]

fixes = C.CDLL("libXfixes.so.3")
fixes.XFixesGetCursorImage.argtypes = [D]
fixes.XFixesGetCursorImage.restype = C.POINTER(CursorImage)


def cursor_image():
    """Compare the actual displayed cursor, independent of theme and serial IDs."""
    pointer = fixes.XFixesGetCursorImage(display)
    assert pointer, "XFixes did not return the displayed cursor"
    try:
        c = pointer.contents
        return (c.width, c.height, c.xhot, c.yhot,
                tuple(c.pixels[i] for i in range(c.width * c.height)))
    finally:
        x.XFree(C.cast(pointer, D))
