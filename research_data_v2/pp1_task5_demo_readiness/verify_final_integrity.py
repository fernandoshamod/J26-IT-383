"""Final read-only integrity comparison against Task 1 and live-run code hashes."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    with (HERE / "demo_execution_results.json").open(encoding="utf-8") as stream:
        baseline = json.load(stream)
    checked = []
    with (ROOT / "research_data_v2/audit_2026-10-17_01/dataset_inventory.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        for row in csv.DictReader(stream):
            path = ROOT / row["path"]
            checked.append({"path": row["path"], "matches_task1":
                            path.is_file() and sha(path) == row["sha256"]})
    code = {
        name: sha(ROOT / name) == earlier
        for name, earlier in baseline["integrity"]["watched_code_sha256"].items()
    }
    result = {
        "task1_file_count": len(checked),
        "task1_hash_matches": sum(item["matches_task1"] for item in checked),
        "task1_hash_mismatches": [x["path"] for x in checked if not x["matches_task1"]],
        "watched_code_file_count": len(code),
        "watched_code_matches_live_run": sum(code.values()),
        "watched_code_mismatches": [name for name, okay in code.items() if not okay],
        "scope": "Current hashes compared with Task 1 inventory and the code hashes captured before live API requests. No pre-task code-hash baseline was available.",
    }
    with (HERE / "final_integrity.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    if result["task1_hash_mismatches"] or result["watched_code_mismatches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()