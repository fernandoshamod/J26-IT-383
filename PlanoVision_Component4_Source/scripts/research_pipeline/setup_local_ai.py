"""Explicit user-invoked local report runtime/model setup; no cloud account."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.local_llm_runtime import ensure_runtime,verified_executable,RUNTIME
from component4.local_llm_report import settings,status


def main():
    if not (RUNTIME/'DOWNLOAD_MANIFEST.json').exists():
        from fetch_ollama_cpu import run
        print('Downloading official CPU runtime entries; no GPU installer required.',flush=True);run(True)
    result=ensure_runtime()
    if result['ready']:print(json.dumps(result,indent=2));return 0
    model=settings()['model'];print('Explicit setup: downloading local model',model,flush=True)
    code=subprocess.call([str(verified_executable()),'pull',model])
    if code:return code
    result=status();print(json.dumps(result,indent=2));return 0 if result['ready'] else 1


if __name__=='__main__':raise SystemExit(main())
