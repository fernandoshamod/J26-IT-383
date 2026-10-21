"""Read-only independent replay of selected preserved PP1 novelty evidence.

This is a raw-record consistency replay, not a new scientific experiment.
Run from C:\\My Research Component with the installed Python environment:
  .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_COMMENT3_FINAL_SCIENTIFIC_RESOLUTION_V1/RAW_EXPERIMENTS_AND_REPRODUCTION/replay_evidence.py
"""
from __future__ import annotations
import hashlib, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\My Research Component")
OUT = ROOT / "PP1_READINESS_20261022/PP1_COMMENT3_FINAL_SCIENTIFIC_RESOLUTION_V1/RAW_EXPERIMENTS_AND_REPRODUCTION/REPLAY_RESULT.json"

def read(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def paired(rows, method_a, method_b, key_fn, fields):
    groups = defaultdict(dict)
    for row in rows:
        if row.get("method") in (method_a, method_b):
            groups[key_fn(row)][row["method"]] = row
    pairs = [v for v in groups.values() if set(v) == {method_a, method_b}]
    mismatches = []
    for idx, pair in enumerate(pairs):
        diffs = [field for field in fields if pair[method_a].get(field) != pair[method_b].get(field)]
        if diffs:
            mismatches.append({"pair_index": idx, "fields": diffs})
    return {"pairs": len(pairs), "matched": len(pairs)-len(mismatches), "mismatches": mismatches}

def main():
    nov = read("PP1_READINESS_20261022/PP1_NOVELTY_VALIDATION_V1/RAW_EXPERIMENT_RESULTS.json")
    eag = paired(nov, "B4", "EAG", lambda r:(r["unit"], r["case"]),
        ["status","expected","comparable","false_accept","false_refusal","operation","evaluations","optimizer_calls","candidates","material_alternatives","protected_changes","geometry_failures","function_omissions","envelope_valid","pool_sha256","metrics"])
    review = read("PP1_READINESS_20261022/PP1_ORIGINAL_RESEARCH_MECHANISM_V1/RAW_REVIEW_RESULTS.json")
    review = paired(review, "B5", "NEW", lambda r:(r["case"],r["budget"],tuple(r["truth"])),
        ["decision","observed","trace","review_cost","posterior","conditional_expected_loss","conditional_plan","conditional_valid","actual_loss","false_conditional_accept","ready","false_readiness","actual_status","missed_mandatory_facts","stage_regret_m","full_information_best_loss","feasible_signature_count","source_anchor_sha256","world_table_sha256","fresh_optimizer_evaluations","qualified_result_sha256","qualified_layout_sha256","qualified_stage_distance_m","conditional_refusal_with_full_information_feasible"])
    recovery_rows = read("PP1_READINESS_20261022/PP1_FEASIBILITY_RECOVERY_NOVELTY_V1/RAW_EXPERIMENT_RESULTS.json")
    recovery = paired(recovery_rows, "GROUPED_CONVENTIONAL", "DECLARATIVE_REFERENCE", lambda r:r["run_id"],
        ["status","authorized_states","screened_proofs","actual_shared_searches","shared_evaluations","verified_witnesses","menu_alternatives","distinct_concessions","hard_violations","protected_violations","best_concession_cost","best_service_m"])
    function_rows = read("PP1_READINESS_20261022/PP1_FUNCTION_USABILITY_RESEARCH_V1/RAW_EXPERIMENT_RESULTS_FINAL.json")
    function = paired(function_rows, "B2", "NEW", lambda r:r["id"].rsplit("_",1)[0],
        [k for k in function_rows[0] if k not in {"id","method","runtime_s","result_path"}])
    # Also compare the actual linked result traces and candidate geometry, excluding only method/runtime labels.
    function_groups = defaultdict(dict)
    for row in function_rows:
        if row.get("method") in ("B2","NEW"):
            function_groups[row["id"].rsplit("_",1)[0]][row["method"]] = row
    function_payload_mismatch=[]
    for key, pair in function_groups.items():
        if set(pair)!={"B2","NEW"}: continue
        payloads=[]
        for m in ("B2","NEW"):
            payload=read(Path(pair[m]["result_path"]).relative_to(ROOT))
            payloads.append({k:v for k,v in payload.items() if k not in {"method","runtime_s"}})
        if payloads[0] != payloads[1]: function_payload_mismatch.append(key)
    focused=read("PP1_READINESS_20261022/PP1_COMMENT3_FOCUSED_SCIENTIFIC_GAP_V1/RESULTS.json")
    knox=read("PP1_READINESS_20261022/PP1_KNOX_REAL_SOURCE_EVENT_AWARE_VALIDATION_V1/RAW_RESULTS/PIXEL_ACCESS_SENSITIVITY.json")
    knox_ind=read("PP1_READINESS_20261022/PP1_KNOX_REAL_SOURCE_EVENT_AWARE_VALIDATION_V1/RAW_RESULTS/INDEPENDENT_VERIFICATION.json")
    cvc=read("PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1/INDEPENDENT_METRIC_VERIFICATION.json")
    checks={
      "eag_b4_pair_replay":eag,
      "review_b5_new_pair_replay":review,
      "function_b2_new_summary_pair_replay":function,
      "function_b2_new_actual_payload_pairs":len(function_groups),
      "function_b2_new_actual_payload_mismatches":function_payload_mismatch,
      "recovery_reference_pair_replay":recovery,
      "focused_controlled_diagnostic": {"rows":len(focused["rows"]),"baseline_matches":focused["method_pair_matches"],"new_model_forwards":focused["new_model_forwards"],"optimizer_evaluations":focused["optimizer_evaluations"]},
      "knox_source_topology_diagnostic": {"cases":len(knox["scenarios"]),"bfs_floyd_agree":all(x["independent_implementation_agreement"] for x in knox["scenarios"]),"independent_assertions_passed":knox_ind.get("passed"),"independent_assertions_total":knox_ind.get("total"),"units":knox["units"],"all_candidate_door_predictions_uncertain":all(x["status"]=="uncertain" for x in knox["door_predictions_used"])},
      "cvc_external_unet_independent_replay": {"status":cvc.get("status"),"assertions_passed":sum(bool(x.get("pass_",x.get("pass",False))) for x in cvc.get("checks",[])),"assertions_total":len(cvc.get("checks",[])),"metric": "pooled native-CVC mIoU 0.2817846732 is a different evaluation target; no reinterpretation as event-function validation"}
    }
    all_pair_checks=[eag,review,function,recovery]
    assert all(x["pairs"]==x["matched"] for x in all_pair_checks)
    assert not function_payload_mismatch
    assert focused["method_pair_matches"]==len(focused["rows"])
    assert checks["knox_source_topology_diagnostic"]["bfs_floyd_agree"]
    # Rehash the prior 724-file snapshot and all directly relevant task evidence.
    prior=read("PP1_READINESS_20261022/PP1_COMMENT3_FOCUSED_SCIENTIFIC_GAP_V1/PRESERVATION_BEFORE.json")
    prior_map=prior if isinstance(prior,dict) else prior.get("files",{})
    old_mismatch=[]
    for rel,expected in prior_map.items():
        p=ROOT/rel
        if not p.is_file() or sha(p)!=expected: old_mismatch.append(rel)
    assert not old_mismatch, f"prior snapshot mismatch: {old_mismatch[:5]}"
    # This current task's evidence-input hashes are recorded in the separate file manifest.
    manifest=read("PP1_READINESS_20261022/PP1_COMMENT3_FINAL_SCIENTIFIC_RESOLUTION_V1/RAW_EXPERIMENTS_AND_REPRODUCTION/SOURCE_EVIDENCE_HASHES.json")
    targeted_mismatch=[]
    for rec in manifest["files"]:
        p=ROOT/rec["path"]
        if not p.is_file() or sha(p)!=rec["sha256"]: targeted_mismatch.append(rec["path"])
    assert not targeted_mismatch, f"task evidence input mismatch: {targeted_mismatch[:5]}"
    result={"schema":"PP1_COMMENT3_RAW_EVIDENCE_REPLAY_V1","status":"PASS_READ_ONLY_REPLAY","scope":"Recomputes selected pair equivalence and preservation hashes; not a new search/inference/venue experiment.","preservation":{"prior_snapshot_files":len(prior_map),"prior_snapshot_unchanged":len(prior_map)-len(old_mismatch),"task_evidence_files":len(manifest["files"]),"task_evidence_unchanged":len(manifest["files"])-len(targeted_mismatch)},"checks":checks,"new_optimizer_searches":0,"new_model_forwards":0,"genuine_review_approvals":0,"real_venue_layouts":0}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
