"""Build with the compiler selected by Mise and the installed raylib package."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
PLUM = subprocess.check_output(["mise", "which", "plum"], cwd=ROOT, text=True).strip()
with (ROOT / "mise.toml").open("rb") as config:
    PLUM_VERSION = tomllib.load(config)["tools"]["github:bradcypert/plum"]
EXE = BUILD / ("powerlaunch.exe" if os.name == "nt" else "powerlaunch")


def native_options():
    if not shutil.which("pkg-config"):
        raise SystemExit("Install raylib and pkg-config first; see README.md for platform prerequisites.")
    try:
        flags = shlex.split(subprocess.check_output(
            ["pkg-config", "--cflags", "--libs", "raylib"], text=True))
    except subprocess.CalledProcessError:
        raise SystemExit("raylib was not found by pkg-config. See README.md.")
    libraries = [flag[2:] for flag in flags if flag.startswith("-l")]
    driver_flags = [flag for flag in flags if not flag.startswith("-l")]
    if os.name == "nt":
        libraries += ["comdlg32", "ole32", "shell32", "uuid"]
    return driver_flags, libraries


def environment():
    if not shutil.which("plum") or not shutil.which("clang"):
        raise SystemExit("Run through Mise, and install Clang. See README.md.")
    actual = subprocess.check_output([PLUM, "--version"], text=True).strip()
    if actual != f"plum {PLUM_VERSION}":
        raise SystemExit(f"Expected Mise's plum {PLUM_VERSION}, got {actual!r}. Run mise install then mise run build.")
    flags, libraries = native_options()
    env = os.environ.copy()
    env["PATH"] = str(Path(PLUM).parent) + os.pathsep + env["PATH"]
    driver = shlex.split(env.get("PLUM_CC", "clang")) + flags
    env["PLUM_CC"] = shlex.join(driver)
    env.setdefault("PLUM_CACHE", str(ROOT / ".cache" / "plum"))
    options = [item for lib in libraries for item in ("--link-lib", lib)]
    return env, options


def build():
    BUILD.mkdir(exist_ok=True)
    env, options = environment()
    subprocess.run([PLUM, "build", "app", "-o", str(EXE), *options],
                   cwd=ROOT, env=env, check=True)
    print(f"Built {EXE}")


if __name__ == "__main__":
    build()
