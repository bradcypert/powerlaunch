"""Real Plum async cover pipeline: cold/warm rendering with full-resolution PNGs."""
from pathlib import Path
import argparse
import json
import os
import shutil
import sys
import struct
import subprocess
import tempfile
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]


def cover(width, height, index):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data) & 0xffffffff)
    rows = bytearray()
    for y in range(height):
        pixel = bytes(((index*29+y//8) % 256, (index*53+y//16) % 256, (index*71) % 256, 255))
        rows.extend(b'\0' + pixel*width)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows, 1)) + chunk(b'IEND', b'')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games', type=int, default=40)
    parser.add_argument('--width', type=int, default=1200)
    parser.add_argument('--height', type=int, default=1800)
    parser.add_argument('--budget-ms', type=float, default=16.7)
    parser.add_argument('--texture-budget-mb', type=int, default=4)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--report', type=Path, default=ROOT/'build/scroll-performance.json')
    args = parser.parse_args()
    if args.games < 10 or args.width < 1 or args.height < 1:
        parser.error('Use at least 10 games and positive source dimensions')
    if args.width * args.height > 16777216 or not 4 <= args.texture_budget_mb <= 64 or args.budget_ms <= 0:
        parser.error('Use sources <=16 megapixels, a 4–64 MiB cache, and a positive time budget')
    (ROOT/'build').mkdir(exist_ok=True)
    sys.path.insert(0,str(ROOT/'scripts'))
    from build import PLUM, environment
    with tempfile.TemporaryDirectory(prefix='powerlaunch-scroll-') as folder:
        project = Path(folder) / 'project'
        project.mkdir()
        shutil.copytree(ROOT/'app/desktop',project/'desktop')
        shutil.copytree(ROOT/'app/native',project/'native')
        shutil.copytree(ROOT/'app/vendor',project/'vendor')
        shutil.copy2(ROOT/'app/plum.pkg',project/'plum.pkg')
        shutil.copy2(ROOT/'tests/cover_scroll.plum',project/'main.plum')
        shutil.copy2(ROOT/'tests/cover_bench_clock.c',project/'native/bench_clock.c')
        # platform/dialog/process sources are copied too to match normal native
        # discovery; only the desktop module is used by the measured program.
        env, options = environment()
        if args.sanitize:
            os.environ['POWERLAUNCH_SANITIZE']='1'
            env, options = environment()
            env.update(ASAN_OPTIONS='detect_leaks=0:halt_on_error=1')
        executable=ROOT/'build'/('cover-scroll.exe' if os.name == 'nt' else 'cover-scroll')
        subprocess.run([PLUM,'build',str(project),'-o',str(executable),*options],cwd=ROOT,env=env,check=True)
        fixtures = Path(folder) / 'images'
        fixtures.mkdir()
        for i in range(args.games):
            path=fixtures/f'cover-{i:04d}.png'
            path.write_bytes(cover(args.width,args.height,i))
        env.update(POWERLAUNCH_MEMORY_REPORT='1',POWERLAUNCH_SCROLL_FIXTURES=str(fixtures),POWERLAUNCH_SCROLL_BUDGET=str(args.budget_ms),POWERLAUNCH_TEXTURE_BUDGET_MB=str(args.texture_budget_mb))
        from profile_memory import process_memory
        samples = []
        log_path = args.report.with_suffix('.log')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open('w') as log:
            process = subprocess.Popen([str(executable)], env=env, stdout=log, stderr=log)
            deadline = time.monotonic() + 60
            try:
                while process.poll() is None:
                    memory = process_memory(process.pid)
                    if memory:
                        samples.append(memory)
                    if time.monotonic() > deadline:
                        raise TimeoutError('Cover benchmark exceeded 60 seconds')
                    time.sleep(0.01)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        output = log_path.read_text(errors='replace')
        reports = [json.loads(line) for line in output.splitlines() if line.startswith('{')]
        diagnostics = [line for line in output.splitlines() if line.startswith('[powerlaunch-')]
        for line in diagnostics:
            print(line)
        if process.returncode:
            print(output[-4000:])
            raise SystemExit(process.returncode)
        assert reports, 'Benchmark did not emit a report'
        assert 'images_after_close=0' in output
        assert 'textures_after_close=0' in output
        report = {**reports[-1], 'source_width': args.width, 'source_height': args.height,
                  'budget_ms': args.budget_ms, 'texture_budget_mb': args.texture_budget_mb,
                  'peak_rss_bytes': max((s['rss_bytes'] for s in samples), default=0),
                  'native_cache': diagnostics}
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
