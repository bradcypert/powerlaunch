"""Actual Plum worker/channel/handle ownership and disposable-cache recovery, without a GPU."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
from scroll_performance import cover

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import PLUM, environment

# Keep native compiler inputs on the checkout filesystem: MSYS2's virtual
# temporary directory is not reliably shared with the Windows Plum binary.
(ROOT / 'build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='powerlaunch-worker-', dir=ROOT / 'build') as folder:
    root = Path(folder)
    (root / 'desktop').mkdir()
    (root / 'native').mkdir()
    shutil.copy2(ROOT / 'app/desktop/covers.plum', root / 'desktop/covers.plum')
    shutil.copy2(ROOT / 'tests/cover_worker.plum', root / 'desktop/check.plum')
    for name in ('covers.c', 'covers.h'):
        shutil.copy2(ROOT / 'app/native' / name, root / 'native' / name)
    (root / 'plum.pkg').write_text('Package { name: "cover-worker-test", native_deps: [] }\n')
    (root / 'main.plum').write_text('use desktop;\nlet main (): Unit = desktop.check_cover_worker(())\n')
    (root / 'cover.png').write_bytes(cover(1200, 1800, 1))
    env, options = environment()
    env.update(POWERLAUNCH_MEMORY_REPORT='1', POWERLAUNCH_SCROLL_FIXTURES=folder)
    output = root / ('worker.exe' if os.name == 'nt' else 'worker')
    subprocess.run([PLUM, 'build', str(root), '-o', str(output), *options], env=env, cwd=ROOT, check=True)
    result = subprocess.run([str(output)], env=env, text=True, capture_output=True, timeout=60)
    print(result.stderr, end='')
    if result.returncode:
        print(result.stdout)
        raise SystemExit(result.returncode)
    assert 'images_after_close=0' in result.stderr, result.stderr
    assert 'textures_after_close=0' in result.stderr, result.stderr
    print('Cover worker: 50 channel/handle cycles, failed decode, corrupt/stale cache, outstanding-request shutdown passed.')
