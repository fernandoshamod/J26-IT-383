"""Concise standalone PP1 demonstration using controlled synthetic fixtures."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from conflict_engine import evaluate_case

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def category_rule(first: str, second: str) -> str:
    target = {first, second}
    with (ROOT / "vendor_compatibility_matrix.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            if {row["service_1"], row["service_2"]} == target:
                return row["base_score"]
    return "unknown"


def render() -> str:
    fixture = json.loads((HERE / "fixtures.json").read_text(encoding="utf-8"))
    by_id = {case["case_id"]: case for case in fixture["cases"]}
    lines = [
        "PlanoVision PP1: vendor-pair and operational conflict proof of concept",
        "All event times, availability, pair outcomes and equipment limits below are SYNTHETIC_TEST.",
        "Actual source option/vendor IDs are identity references only; no real booking is confirmed.",
    ]
    for name in ("compatible_pair", "equipment_insufficient", "unknown_pair"):
        case = by_id[name]
        result = evaluate_case(case)
        event = case["event"]
        lines.extend(("", f"CASE {name}: {event['event_id']} | {event['city']}, {event['state']}",
                      f"Event interval: {event['start_at']} to {event['end_at']}",
                      "Selected vendor options:"))
        for item in case["assignments"]:
            lines.append(f"  {item['service_category']}: {item['vendor_id']} / {item['option_id']}")
        pair = result["pair_results"][0]
        lines.append(f"Pair evidence: {pair['status']} | {', '.join(pair['evidence_ids']) or 'none'}")
        lines.append(
            "Category rule context: "
            + category_rule(case["assignments"][0]["service_category"],
                            case["assignments"][1]["service_category"])
            + "/100 (service categories only; NOT vendor collaboration evidence)"
        )
        operational = [check for check in result["checks"]
                       if check["code"].startswith(("resource:", "same_vendor_", "setup_teardown:"))]
        lines.append("Scheduling/equipment checks: " + (
            "; ".join(f"{item['code']}={item['status']}" for item in operational)
            if operational else "no conflict from supplied operational constraints"))
        lines.append(f"Scoped result: {result['status']}")
        lines.append("Explanation: " + " ".join(result["explanation"]))
        lines.append("Venue suitability: VERIFICATION_REQUIRED (external team)")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    output = render()
    print(output, end="")
    if args.save:
        target = HERE / "demo_output.txt"
        with target.open("x", encoding="utf-8") as stream:
            stream.write(output)


if __name__ == "__main__":
    main()
