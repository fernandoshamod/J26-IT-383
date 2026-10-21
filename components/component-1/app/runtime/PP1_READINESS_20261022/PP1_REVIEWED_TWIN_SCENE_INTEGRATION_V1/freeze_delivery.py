"""Freeze this isolated delivery; runtime caches are explicitly excluded."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXCLUDED = {'runtime', '__pycache__'}
MANIFEST = ROOT / 'DELIVERY_SHA256.json'
REGISTER = ROOT / 'FILE_REGISTER.csv'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

if MANIFEST.exists() or REGISTER.exists():
    raise FileExistsError('Preserve the existing delivery freeze')
paths = sorted(p for p in ROOT.rglob('*') if p.is_file()
               and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
               and p not in (MANIFEST, REGISTER))
files = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
with REGISTER.open('x', encoding='utf-8', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['path', 'bytes', 'sha256'])
    for p in paths:
        key = p.relative_to(ROOT).as_posix()
        writer.writerow([key, p.stat().st_size, files[key]])
files[REGISTER.name] = sha(REGISTER)
with MANIFEST.open('x', encoding='utf-8') as stream:
    json.dump({'scope': 'Isolated integration delivery only',
               'excluded_directories': sorted(EXCLUDED),
               'manifest_self_excluded': True, 'files': files}, stream, indent=2)
saved = json.loads(MANIFEST.read_text(encoding='utf-8'))
bad = [name for name, expected in saved['files'].items() if sha(ROOT / name) != expected]
print(json.dumps({'registered_files': len(files), 'hash_mismatches': bad,
                  'status': 'PASS' if not bad else 'FAIL'}))
assert not bad
