"""Real Plum exporter fault/ownership tests plus independent ZIP/extraction checks."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import PLUM, environment
from profile_memory import process_memory, seed_library

(ROOT / 'build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='powerlaunch-backup-', dir=ROOT / 'build') as folder:
    directory = Path(folder)
    project = directory / 'project'
    shutil.copytree(ROOT / 'app', project)
    shutil.copy2(ROOT / 'tests/backup_fixture.plum', project / 'backup/check.plum')
    (project / 'main.plum').write_text('use backup;\nlet main (): Unit = backup.check_backup_fixture(())\n')
    data = directory / 'Café library'
    data.mkdir()
    seed_library(data, 3)
    (data / 'artwork').mkdir()
    covers = {'Café cover.png': bytes(range(256)) * 8192, 'other.jpg': b'\x00\xff\x80cover bytes'}
    for name, content in covers.items():
        (data / 'artwork' / name).write_bytes(content)
    (data / 'artwork/orphan.png').write_bytes(b'excluded orphan')
    for name in ('drafts', 'thumbnails-v1', 'game files', 'saves'):
        (data / name).mkdir()
        (data / name / 'excluded').write_bytes(b'not backup content')
    original = json.loads((data / 'library.json').read_text())
    for i, game in enumerate(original['games']):
        game['cover'] = list(covers)[i % 2]
        game['title'] = f'Café game {i}'
        game['arguments'] = ['', 'two words', 'literal;$(nothing)']
    (data / 'library.json').write_text(json.dumps(original), encoding='utf-8')
    env, options = environment()
    # Pass an ASCII root across the Windows CRT environment boundary; the
    # Plum fixture appends the Unicode child so Unicode file I/O is still tested.
    env['POWERLAUNCH_BACKUP_FIXTURE'] = str(directory)
    output = ROOT / 'build' / (directory.name + '-check' + ('.exe' if os.name == 'nt' else ''))
    subprocess.run([PLUM, 'build', str(project.relative_to(ROOT)), '-o', str(output.relative_to(ROOT)), *options], env=env, cwd=ROOT, check=True)
    log_path = ROOT / 'build/backup-integration.log'
    samples = []
    start = time.monotonic()
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([str(output)], cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            while process.poll() is None:
                sample = process_memory(process.pid)
                if sample:
                    samples.append(sample)
                if time.monotonic() - start > 120:
                    raise TimeoutError('Backup fixture exceeded 120 seconds')
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            output.unlink(missing_ok=True)
    print(log_path.read_text(errors='replace')[-5000:])
    assert process.returncode == 0, process.returncode
    with zipfile.ZipFile(data / 'Café backup.zip') as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'backup.json', 'library.json', *('artwork/' + name for name in covers)}
        assert json.loads(archive.read('library.json')) == original
        manifest = json.loads(archive.read('backup.json'))
        assert (manifest['format'], manifest['version'], manifest['games'], manifest['covers']) == ('powerlaunch-library-backup', 1, 3, 2)
        assert set(manifest['excluded']) == {'game installations', 'game saves', 'thumbnails', 'temporary drafts'}
        for name, content in covers.items():
            assert archive.read('artwork/' + name) == content
        restored = directory / 'independent extraction'
        archive.extractall(restored)
        assert json.loads((restored / 'library.json').read_text()) == original
    with zipfile.ZipFile(data / 'empty.zip') as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'backup.json', 'library.json'}
        assert json.loads(archive.read('library.json'))['games'] == []
    report = {'seconds': round(time.monotonic() - start, 3), 'peak_rss_bytes': max((s['rss_bytes'] for s in samples), default=0),
              'source_cover_bytes': sum(map(len, covers.values())), 'sanitized': env.get('POWERLAUNCH_SANITIZE') == '1',
              'note': 'Repeated 2 MiB cover export/failure fixture; process RSS includes runtime/native libraries and sanitizer overhead when enabled.'}
    (ROOT / 'build/backup-memory.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Independent Python ZIP/read/extract validation passed.', json.dumps(report))
