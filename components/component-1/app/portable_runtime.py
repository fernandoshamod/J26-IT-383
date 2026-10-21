"""Shared package-relative paths and configuration for the portable services."""
from pathlib import Path
import os

PACKAGE_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = PACKAGE_ROOT / "runtime"
STATE_ROOT = Path(os.environ.get("PP1_RUNTIME_STATE", PACKAGE_ROOT / "runtime-state")).resolve()
PRIVATE_ROOT = Path(os.environ.get("PP1_PRIVATE_ASSETS", PACKAGE_ROOT / "private-assets")).resolve()
PORTS = {
    "frontend": int(os.environ.get("PP1_FRONTEND_PORT", "5173")),
    "backend": int(os.environ.get("PP1_BACKEND_PORT", "8765")),
    "companion": int(os.environ.get("PP1_COMPANION_PORT", "8768")),
    "scene": int(os.environ.get("PP1_SCENE_PORT", "8769")),
}
if any(not 1024 <= port <= 65535 for port in PORTS.values()) or len(set(PORTS.values())) != len(PORTS):
    raise ValueError("PORTS_MUST_BE_DISTINCT_VALID_UNPRIVILEGED_PORTS")
