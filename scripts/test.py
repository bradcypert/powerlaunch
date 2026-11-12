from build import BUILD, ROOT, PLUM, environment
import os
import subprocess
import sys

if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    env, options = environment()
    subprocess.run([PLUM, "test", "app", *options], cwd=ROOT, env=env, check=True)
    subprocess.run([sys.executable, "tests/process_integration.py"], cwd=ROOT, env=env, check=True)
    subprocess.run([sys.executable, "tests/clipboard_integration.py"], cwd=ROOT, env=env, check=True)

    subprocess.run([sys.executable, "tests/cover_worker.py"], cwd=ROOT, env=env, check=True)

    subprocess.run([sys.executable, "tests/backup_integration.py"], cwd=ROOT, env=env, check=True)
