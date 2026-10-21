"""Verify portable source integrity and installed runtime dependencies."""
import hashlib
import importlib.metadata as md
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PORTABLE_SOURCE_MANIFEST.json"
REQUIREMENTS = ROOT / "requirements-cpu.txt"
PACKAGES = ["fastapi", "uvicorn", "pydantic", "shapely", "numpy", "scipy", "Pillow", "torch", "torchvision", "segmentation-models-pytorch", "ultralytics", "opencv-python", "pymoo", "psutil", "httpx"]

def verify():
    errors=[]
    if sys.version_info[:2] != (3, 12): errors.append({"reason":"PYTHON_312_REQUIRED", "version":sys.version})
    if not MANIFEST.is_file(): errors.append({"reason":"PORTABLE_SOURCE_MANIFEST_MISSING"})
    else:
        data=json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
        for row in data.get("files",[]):
            path=(ROOT/row["path"]).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file(): errors.append({"reason":"SOURCE_FILE_MISSING_OR_UNSAFE", "path":row["path"]}); continue
            h=hashlib.sha256(path.read_bytes()).hexdigest()
            if h != row["sha256"]: errors.append({"reason":"SOURCE_HASH_MISMATCH", "path":row["path"]})
    for package in PACKAGES:
        try:
            version=md.version(package)
            if package=="torch" and "+cpu" not in version: errors.append({"reason":"CPU_TORCH_REQUIRED", "version":version})
        except Exception as exc: errors.append({"reason":"DEPENDENCY_MISSING", "package":package, "detail":str(exc)})
    if not REQUIREMENTS.is_file(): errors.append({"reason":"CPU_REQUIREMENTS_MISSING"})
    return {"status":"PASS" if not errors else "FAIL", "python":sys.version, "errors":errors, "model_weights_loaded":False}

if __name__ == "__main__":
    result=verify(); print(json.dumps(result,indent=2)); raise SystemExit(0 if result["status"]=="PASS" else 2)
