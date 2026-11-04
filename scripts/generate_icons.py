"""Regenerate checked-in icon assets from SVG; development only (librsvg CLI)."""
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
images = []
for size in [16, 24, 32, 48, 64, 128, 256]:
    images.append((size, subprocess.check_output([
        "rsvg-convert", "-w", str(size), "-h", str(size), str(ROOT / "assets/powerlaunch.svg")])))
offset = 6 + len(images) * 16
directory = bytearray(struct.pack("<HHH", 0, 1, len(images)))
for size, data in images:
    directory += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
    offset += len(data)
(ROOT / "assets/powerlaunch.ico").write_bytes(directory + b"".join(data for _, data in images))
png = images[-1][1]
(ROOT / "assets/powerlaunch.png").write_bytes(png)
rows = [", ".join(str(n) for n in png[i:i+20]) for i in range(0, len(png), 20)]
(ROOT / "app/native/icon_data.h").write_text(
    "/* Generated from assets/powerlaunch.svg by scripts/generate_icons.py. */\n"
    "static const unsigned char powerlaunch_icon[] = {\n    " + ",\n    ".join(rows) + "\n};\n", encoding="utf-8")
