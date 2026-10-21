"""Create a fresh SHA-256 manifest for the portable code and lockfiles."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PORTABLE_SOURCE_MANIFEST.json"
EXCLUDED = {"node_modules", ".venv", "dist", "runtime-state", "private-assets", "__pycache__"}

def main():
    rows = []
    paths = []
    for base in (ROOT / "runtime", ROOT / "frontend"):
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in EXCLUDED for part in path.parts):
                continue
            paths.append(path)
    paths.extend(ROOT/name for name in ["portable_runtime.py", "launcher.py", "verify_portable.py", "build_portable_manifest.py", "requirements-cpu.txt"] if (ROOT/name).is_file())
    for path in sorted(set(paths)):
        rel = path.relative_to(ROOT).as_posix()
        if rel.endswith((".pyc", ".sqlite", ".sqlite3", ".log")):
            continue
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"path": rel, "sha256": h, "bytes": path.stat().st_size})
    MANIFEST.write_text(json.dumps({"schema":"PP1_PORTABLE_SOURCE_V1", "files":rows}, indent=2), encoding="utf-8")
    print(json.dumps({"status":"WRITTEN", "files":len(rows)}, indent=2))

if __name__ == "__main__": main()
