"""Create Stage 7 planning metadata only; never generate financial scenarios or approvals."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "bulk-plan.0.1-proposed"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def dump(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main():
    context_path = "config/minimal_pilot_candidate.json"
    context = json.loads((ROOT / context_path).read_text(encoding="utf-8-sig"))
    for existing in ("config/bulk_generation_candidate.json", "reports/final_dataset_manifest.candidate.json"):
        if (ROOT / existing).exists():
            old = json.loads((ROOT / existing).read_text(encoding="utf-8-sig"))
            assert old.get("status") == "blocked_unapproved_unfrozen", "Refuse to replace reviewed/frozen artifacts"
            assert not old.get("authorization", {}).get("explicitly_authorized"), "Refuse to overwrite authority"
            assert not old.get("freeze", {}).get("complete"), "Refuse to overwrite frozen artifacts"
    status = context["minimal_recovery"]["completeness"]
    code_paths = ("component4/engine.py", "component4/scenario_generator.py",
                  "component4/generator_validation.py", "component4/gates.py")
    sources = {p: {"expected_context_sha256": h, "current_sha256": sha(p),
                   "matches_context": sha(p) == h, "approved_frozen": False}
               for p, h in context["source_snapshot_hashes"].items()}
    assert all(v["matches_context"] for v in sources.values()), "Context source changed; review first"
    assert not status["candidate_complete"] and not status["frozen_configuration_sha256"], "Reaudit changed readiness"
    assert not (ROOT / "data/pilot").exists(), "Pilot directory appeared; inspect actual results before refreshing plan"
    ancestries = {event: profile["ancestry"] for event, profile in context["scenario_generator"]["profiles"].items()}
    assert len({a["venue_profile_id"] for a in ancestries.values()}) == 1, "Reaudit source-group feasibility"
    proposed = {
        "document_kind": "NON_EXECUTABLE_BULK_PLANNING_PROPOSAL",
        "version": VERSION, "prepared_date": "2026-10-11", "status": "blocked_unapproved_unfrozen",
        "warning": "SYNTHETIC SIMULATOR DESIGN — NOT OBSERVED EVENTS, QUOTATIONS OR TRAINED PREDICTIONS",
        "execution_enabled": False,
        "simulator_context": {"path": context_path, "draft_file_sha256": sha(context_path),
                              "version": context["config_version"], "candidate_complete": False,
                              "frozen_configuration_sha256": None, "approved_configuration_version": None},
        "prerequisites": {"diagnostic_pilot_generated": False, "stage6_mandatory_criteria_passed": False,
                          "formal_formula_reviews_pending": status["formulas_pending"],
                          "formal_numeric_reviews_pending": status["formal_numeric_reviews_pending"],
                          "proposed_active_numeric_nulls": status["active_proposal_numeric_nulls"],
                          "engine_numeric_nulls": status["current_engine_numeric_nulls"],
                          "proposed_excluded_numeric_slots": status["proposed_excluded_numeric_slots"],
                          "effective_engine_disabled_slots": status["effective_engine_disabled_slots"],
                          "expanded_generator_implemented": False, "expanded_generator_diagnostic_passed": False},
        "proposed_size": {"target_rows": 7500, "root_configurations": 1250,
                          "planning_states_per_root_including_base": 3, "controlled_variants_per_root": 2,
                          "outcome_replications_per_planning_state": 2, "planning_states": 3750,
                          "rows_per_root": 6, "population_frequency_claim": False,
                          "independent_observed_event_count": 0,
                          "effective_independent_source_sample_size": None,
                          "root_independence_claim": "conditional design draws, not IID real events; deduplication and shared sources disclosed",
                          "archetypes": {e: {"root_count": 625, "row_count": 3750, "approval_status": "pending"}
                                        for e in ("Wedding", "Corporate")}},
        "proposed_sampling": {"seed": 20261022, "split_seed": 20261023, "approval_status": "pending",
                              "root_sampling": "reviewed domains; exact event quotas; unique root planning fingerprints within archetype",
                              "max_planning_attempts_per_root": 20, "deduplication": "sampling_without_replacement_disclosed",
                              "variants": [{"id": "base", "guest_delta_persons": 0},
                                           {"id": "guest_minus_1", "guest_delta_persons": -1},
                                           {"id": "guest_plus_1", "guest_delta_persons": 1}],
                              "proposed_root_guest_support": {"Wedding": {"min": 91, "max": 179, "unit": "persons"},
                                                              "Corporate": {"min": 41, "max": 119, "unit": "persons"}},
                              "support_status": "new experimental restriction pending review; derive anew if approved bounds change",
                              "hold_fixed_within_family": ["date", "duration", "stage", "venue", "budget", "expected_retained_receipts", "rate_card"],
                              "recompute_derived_quantities": True,
                              "paired_realizations_across_variants": True,
                              "ordinary_cost_dependence": "one common factor across approved cost services; receipts factor separately drawn",
                              "outcome_parameters": "inherit ONLY future complete reviewed simulator; no new financial rate defaults",
                              "outcome_sampling_for_label_balance": False,
                              "retain_financially_risky_valid_states": True},
        "proposed_split": {"policy": "transitive_shared_source_and_planning_fingerprint_components",
                           "restricted_ancestry_keys": ["venue_profile_id", "vendor_rate_card_id", "archetype_template_id"],
                           "underlying_source_dependency_ids_required": True,
                           "source_dependency_taxonomy_approval": "pending",
                           "identical_planning_states_merge_groups": True, "keep_all_family_descendants_together": True,
                           "target_row_fractions": {"train": 0.70, "validation": 0.15, "test": 0.15},
                           "max_absolute_fraction_deviation": 0.05, "minimum_components": 3,
                           "current_context_components": 1, "current_context_feasible": False,
                           "assignment_rule": "largest component first; seeded SHA256 tie break; first three train/validation/test; remaining greatest positive target deficit",
                           "assignment_timing": "after planning/provenance, before realized outcomes",
                           "split_map_sha256": None, "weaker_family_only_policy_selected": False,
                           "approval_status": "pending"},
        "quality": {"approval_status": "pending", "criteria_path": "reports/final_dataset_generation_plan.md",
                    "required_accounting_capacity_label_provenance_pass_fraction": 1.0,
                    "duplicate_scenario_ids_allowed": 0, "cross_split_related_groups_allowed": 0,
                    "mandatory_active_missing_values_allowed": 0,
                    "planning_attempt_rejection_warning_fraction": 0.10,
                    "label_proportion_targets": None, "unavailable_margin_policy": "explicit_null_and_mask_not_healthy_zero",
                    "real_world_accuracy_claim": False},
        "processing_estimates": {"status": "engineering_estimates_not_measured", "average_jsonl_bytes_per_scenario": 35400,
                                 "estimated_primary_output_bytes": 265500000, "ledger_rows_upper_projection": 210000,
                                 "proposed_future_batch_rows": 250, "streaming_implemented": False,
                                 "provisional_memory_budget_gib": [1, 3], "runtime_seconds": None},
        "freeze": {"complete": False, "approved_code_revision": None, "code_archive_sha256": None,
                   "source_manifest_sha256": None, "split_policy_sha256": None,
                   "split_map_sha256": None, "split_map_creation_phase": "authorized planning before outcomes; execution-manifest artifact",
                   "acceptance_criteria_sha256": None, "canonical_bulk_authorization_payload_sha256": None},
        "authorization": {"status": "not_eligible_for_execution_decision", "explicitly_authorized": False,
                          "reviewer": None, "reviewer_role": None, "date": None, "rationale": None,
                          "evidence_reference": None, "authorized_scenario_count": None, "approved_payload_sha256": None},
        "forbidden_actions": ["pilot_generation", "bulk_generation", "model_training", "fabricated_approvals", "pilot_gate_bypass"]}
    counts = proposed["proposed_size"]
    assert counts["root_configurations"] * counts["planning_states_per_root_including_base"] * counts["outcome_replications_per_planning_state"] == counts["target_rows"]
    candidate_path = "config/bulk_generation_candidate.json"
    dump(candidate_path, proposed)
    documents = ["reports/final_dataset_generation_plan.md", "reports/final_sampling_strategy.md",
                 "reports/bulk_generation_authorization.md"]
    artifacts = ["prediction_features.jsonl", "simulated_outcomes.jsonl", "planned_line_items.jsonl",
                 "realized_line_items.jsonl", "scenario_provenance.jsonl", "latent_outcomes_DO_NOT_USE_AS_FEATURES.jsonl",
                 "rejected_configurations.jsonl", "split_map.json", "configuration.json", "manifest.json"]
    manifest = {
        "manifest_version": VERSION, "document_kind": "CANDIDATE_NOT_A_GENERATED_DATASET_MANIFEST",
        "prepared_date": "2026-10-11", "status": "blocked_unapproved_unfrozen", "generated_scenario_count": 0,
        "proposed_counts": counts, "candidate_plan_path": candidate_path, "candidate_plan_file_sha256": sha(candidate_path),
        "hash_semantics": "All hashes below identify current draft context only; none assert formal approval or frozen configuration",
        "documents_current_sha256": {p: sha(p) for p in documents},
        "simulator_context": proposed["simulator_context"],
        "code_current_sha256": {p: sha(p) for p in code_paths}, "approved_code_revision": None,
        "sources_current_context": sources, "ancestry_current_context": ancestries,
        "runtime_context_not_frozen": context["scenario_generator"]["software_versions"],
        "preexisting_final_artifacts_preserved": {
            p.relative_to(ROOT).as_posix(): {"sha256": sha(p.relative_to(ROOT)), "bytes": p.stat().st_size}
            for p in sorted((ROOT / "data/final").rglob("*")) if p.is_file()},
        "preexisting_final_data_disposition": "earlier partial observed context/time-series artifacts; not an authorized financial pilot or bulk run",
        "prerequisite_status": proposed["prerequisites"], "split_status": proposed["proposed_split"],
        "proposed_output_contract": {"directory": "data/final/<approved_version_and_run_identity>/",
                                     "directory_created": False, "artifacts": artifacts,
                                     "artifact_sha256": None, "optional_flat_csv_export_requires_review": True,
                                     "feature_allowlist_reference": "component4/scenario_generator.py:FEATURE_UNITS",
                                     "origin": "synthetic_simulator; never_observed_events", "overwrite_existing": False},
        "freeze": proposed["freeze"], "authorization": proposed["authorization"],
        "required_new_implementation": ["exact_archetype_quotas", "variants", "paired_replications", "replication_aware_rng_and_ids",
                                        "connected_component_ancestry_splits", "frozen_split_map", "bulk_only_approval_gate_and_writer",
                                        "reviewed_exclusion_or_complete_original_rates", "truthful_reviewed_geometry_contract"],
        "generation_and_training_performed": False}
    dump("reports/final_dataset_manifest.candidate.json", manifest)
    print(json.dumps({"status": "BLOCKED: planning metadata only", "proposed_rows": counts["target_rows"],
                      "roots": counts["root_configurations"], "candidate_plan_sha256": sha(candidate_path),
                      "frozen_configuration_sha256": None, "current_source_components": 1,
                      "generated_rows": 0}, indent=2))


if __name__ == "__main__":
    main()
