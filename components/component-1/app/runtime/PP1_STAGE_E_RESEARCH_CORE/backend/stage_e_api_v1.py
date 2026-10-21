import hashlib
import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
OUTPUTS = ROOT / "outputs"

MANIFEST = (
    ROOT
    / "PP1_STAGE_E_INTEGRATION_V2"
    / "INTEGRATION_MANIFEST_V2.json"
)

sys.path.insert(0, str(RESEARCH))

from f2h_unified_dispatcher_v2 import dispatch

app = FastAPI(
    title="Stage E PP1 Research API",
    version="1.0.0",
    description="Controlled synthetic research integration only",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_engine():
    manifest = json.loads(
        MANIFEST.read_text(encoding="utf-8")
    )

    if manifest["integration_id"] != "PP1_STAGE_E_INTEGRATION_V2":
        raise RuntimeError("Invalid integration manifest")

    for name, expected in manifest["source_hashes"].items():
        source = RESEARCH / name
        if not source.is_file() or sha256(source) != expected:
            raise RuntimeError(f"Research source hash mismatch: {name}")

    for name, expected in manifest["evidence_hashes"].items():
        evidence = OUTPUTS / name
        if not evidence.is_file() or sha256(evidence) != expected:
            raise RuntimeError(f"Research evidence hash mismatch: {name}")

    return True


@app.get("/api/stage-e/health")
def health():
    try:
        verify_frozen_engine()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="RESEARCH_INTEGRITY_CHECK_FAILED",
        )

    return {
        "status": "ready",
        "contract_id": "STAGE_E_PP1_V1",
        "engine": "PP1_STAGE_E_INTEGRATION_V2",
        "modes": ["initial_design", "adaptive_revision"],
        "controlled_synthetic_only": True,
        "real_planner_authentication": False,
        "real_venue_supported": False,
    }


@app.post("/api/stage-e/optimize")
async def optimize(request: Request):
    try:
        verify_frozen_engine()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="RESEARCH_INTEGRITY_CHECK_FAILED",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="INVALID_JSON",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=422,
            detail="INVALID_REQUEST",
        )

    try:
        response = dispatch(payload)
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="RESEARCH_ENGINE_EXECUTION_FAILED",
        )

    if response["status"] == "denied":
        # Do not expose candidate layouts on denied requests.
        if response["candidate_layouts"]:
            raise HTTPException(
                status_code=500,
                detail="DENIED_LAYOUT_INTEGRITY_FAILURE",
            )

        return {
            **response,
            "api_notice": "SIMULATED_PERMISSION_DENIAL",
        }

    return response