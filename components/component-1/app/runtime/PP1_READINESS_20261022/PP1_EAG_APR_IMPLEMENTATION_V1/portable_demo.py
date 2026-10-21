"""Run the actual controlled EAG-APR approval and singleton-repair workflow."""
from __future__ import annotations
import argparse, copy, json, re, time
from pathlib import Path
from runtime import *
import core
from scenarios import initial, change
from repair import run, make_reference
import authority

PACKAGE_ROOT = HERE.parents[2]
STATE_ROOT = PACKAGE_ROOT / "runtime-state" / "eag-apr"

def main(run_id: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", run_id):
        raise ValueError("Run ID may contain only letters, digits, _ and - (max 60).")
    out = (STATE_ROOT / run_id).resolve()
    if not out.is_relative_to(STATE_ROOT.resolve()):
        raise ValueError("Output path must remain inside ignored runtime-state/eag-apr.")
    out.mkdir(parents=True, exist_ok=False)
    # Keep source/policy reads package-relative while directing all generated
    # evidence, certificates and run records to ignored portable runtime state.
    common.HERE = out
    common.ROOT = PACKAGE_ROOT
    core.ROOT = PACKAGE_ROOT
    authority.ROOT = PACKAGE_ROOT
    fixtures.HERE = SCENE
    bridge.HERE = out
    started = time.perf_counter()

    packet = initial(out / "BASE_INPUT", 32, 24)
    initial_result, graph = run(packet, out / "INITIAL_EAG", "EAG", 20261017)
    if initial_result["status"] != "eligible":
        raise RuntimeError("CONTROLLED_INITIAL_LAYOUT_NOT_ELIGIBLE")
    reference = make_reference(packet["scene"], initial_result, graph, out / "INITIAL_EAG")

    context = copy.deepcopy(packet["context"])
    context.update(version=2, reference_sha256=digest(reference["layout"]),
                   allowed_groups=sorted(reference["layout"]["group_centers_m"]))
    approved = seal_packet(packet["scene"], context, out / "SIMULATED_APPROVAL")
    approval_result, approval_graph = run(approved, out / "APPROVAL_EAG", "EAG", 20261017, reference)
    if approval_result["status"] != "eligible" or approval_result["optimizer_evaluations"] != 0:
        raise RuntimeError("EXPLICIT_SIMULATED_APPROVAL_GATE_FAILED")
    reference.update(certificate=approval_result["certificate"], graph=approval_graph,
                     pool=approval_result["candidate_layouts"])

    revised = change("authorized_singleton_repair", approved, reference, out / "SINGLETON_CHANGE_INPUT")
    result, _ = run(revised, out / "ADAPTIVE_EAG", "EAG", 20261017, reference)
    if result["status"] != "eligible" or result["optimizer_evaluations"] < 1 or not result["candidate_layouts"]:
        raise RuntimeError("CONTROLLED_SINGLETON_REPAIR_NOT_ELIGIBLE")

    summary = {
        "scope": "CONTROLLED_SYNTHETIC_SIMULATED_AUTHORITY_NOT_REAL_VENUE",
        "initial_status": initial_result["status"],
        "initial_evaluations": initial_result["optimizer_evaluations"],
        "approval_status": approval_result["status"],
        "approval_search_evaluations": approval_result["optimizer_evaluations"],
        "repair_status": result["status"],
        "repair_operation": result["operation"],
        "repair_evaluations": result["optimizer_evaluations"],
        "repair_candidates": len(result["candidate_layouts"]),
        "full_fallback": result["fallback"],
        "previous_candidates_invalidated": len(result["invalidated_previous_candidates"]),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "output_directory": str(out),
        "human_approval": False,
        "real_venue_qualification": False,
    }
    save(out / "PORTABLE_DEMO_SUMMARY.json", summary)
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="Unique output folder name")
    raise SystemExit(main(parser.parse_args().run))
