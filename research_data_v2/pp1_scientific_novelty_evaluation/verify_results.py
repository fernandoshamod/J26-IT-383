"""Read-only consistency checks for isolated PP1 evaluation outputs."""
import csv
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
def rows(name):
    with (HERE/name).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))
def main():
    ranking=rows("baseline_comparison.csv")
    search=rows("search_quality_comparison.csv")
    conflict=rows("conflict_comparison.csv")
    result=json.loads((HERE/"summary.json").read_text(encoding="utf-8-sig"))
    assert len(ranking)==len(search)==8
    assert len(conflict)==12
    for row in ranking:
        if row["baseline_cost_lkr"]:
            assert float(row["baseline_cost_lkr"])<=float(row["proposed_cost_lkr"])+1e-6
            assert row["baseline_budget_compliant"]==row["proposed_budget_compliant"]=="True"
            assert row["baseline_coverage"]==row["proposed_coverage"]=="True"
    for row in search:
        assert int(row["exhaustive_feasible_count"])>=int(row["bounded_feasible_count"])
        assert int(row["missed_feasible_combinations"])==int(row["exhaustive_feasible_count"])-int(row["bounded_feasible_count"])
        if row["candidate_truncated"]=="False" and row["node_truncated"]=="False":
            assert int(row["missed_feasible_combinations"])==0
        if row["best_score_regret"]:
            assert float(row["best_score_regret"])>=0
    assert all(row["evidence_type"]=="SYNTHETIC_TEST" for row in conflict)
    assert sum(row["correct"]=="True" for row in conflict)==result["conflict"]["correct_statuses"]
    assert sum(int(row["missed_feasible_combinations"]) for row in search)==result["search"]["total_missed_feasible"]
    print("PASS: output row counts, pairing, constraints, search counts and synthetic conflict labels")
if __name__=="__main__":main()

