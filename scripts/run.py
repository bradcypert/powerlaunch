from build import EXE, ROOT
import subprocess

if __name__ == "__main__":
    raise SystemExit(subprocess.call([str(EXE)], cwd=ROOT))
