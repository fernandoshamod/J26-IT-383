import json
import sys
from pathlib import Path

from f2b_live_research_engine_v1 import run as run_initial
from f2d_live_adaptive_engine_v1 import execute as run_adaptive

CONTRACT = "STAGE_E_PP1_V1"

def dispatch(request):
    if not isinstance(request, dict):
        raise ValueError("INVALID_REQUEST")

    if request.get("contract_id") != CONTRACT:
        raise ValueError("INVALID_CONTRACT")

    mode = request.get("mode")

    if mode == "initial_design":
        response = run_initial(request)
    elif mode == "adaptive_revision":
        response = run_adaptive(request)
    else:
        raise ValueError("UNSUPPORTED_MODE")

    if response.get("contract_id") != CONTRACT:
        raise RuntimeError("RESPONSE_CONTRACT_MISMATCH")

    if response.get("status") not in (
        "success", "infeasible", "denied", "error"
    ):
        raise RuntimeError("INVALID_RESPONSE_STATUS")

    if not isinstance(response.get("candidate_layouts"), list):
        raise RuntimeError("INVALID_LAYOUT_OUTPUT")

    if response["status"] == "denied":
        if response["candidate_layouts"]:
            raise RuntimeError("DENIED_REQUEST_HAS_LAYOUTS")
        if response["provenance"].get(
            "optimizer_evaluations", -1
        ) != 0:
            raise RuntimeError("DENIED_REQUEST_RAN_OPTIMIZER")

    if response["status"] == "success":
        if not response["candidate_layouts"]:
            raise RuntimeError("SUCCESS_WITHOUT_LAYOUTS")
        if not response["validation_flags"].get(
            "synthetic_geometry_pass", False
        ):
            raise RuntimeError("UNVERIFIED_SUCCESS")

        for layout in response["candidate_layouts"]:
            objects = layout["objects"]
            ids = [obj["object_id"] for obj in objects]
            if len(ids) != len(set(ids)):
                raise RuntimeError("DUPLICATE_OBJECT_IDS")

    return response


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: dispatcher.py request.json output.json"
        )

    request_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if output_path.exists():
        raise FileExistsError(
            "Output exists; refusing overwrite"
        )

    request = json.loads(
        request_path.read_text(encoding="utf-8")
    )
    response = dispatch(request)

    output_path.write_text(
        json.dumps(response, indent=2),
        encoding="utf-8",
    )

    print("=== F2E UNIFIED STAGE E DISPATCHER ===")
    print("Mode:", request["mode"])
    print("Status:", response["status"])
    print("Layouts:", len(response["candidate_layouts"]))
    print(
        "Optimizer evaluations:",
        response["provenance"]["optimizer_evaluations"]
    )
    print("Output:", output_path)