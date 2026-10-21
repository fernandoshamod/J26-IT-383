"""Service-category compatibility heuristics; no vendor collaboration evidence."""

from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MATRIX_FILE = ROOT / "vendor_compatibility_matrix.csv"


def load_compatibility_rules():
    matrix = pd.read_csv(MATRIX_FILE)
    required = {"service_1", "service_2", "base_score"}
    if not required.issubset(matrix.columns):
        raise ValueError("Compatibility matrix lacks required service-pair columns")
    rules = {}
    for row in matrix.itertuples(index=False):
        pair = tuple(sorted((str(row.service_1).strip(), str(row.service_2).strip())))
        score = float(row.base_score)
        if pair in rules or not 0 <= score <= 100:
            raise ValueError(f"Invalid or duplicate compatibility rule: {pair}")
        rules[pair] = score
    return rules


def service_compatibility(services, rules):
    pairs = []
    unknown = []
    for service_a, service_b in combinations(services, 2):
        key = tuple(sorted((service_a, service_b)))
        score = rules.get(key)
        item = {
            "service_1": service_a,
            "service_2": service_b,
            "score": score,
            "status": "known" if score is not None else "unknown",
        }
        pairs.append(item)
        if score is None:
            unknown.append([service_a, service_b])
    if not pairs:
        status = "not_applicable"
        score = None
    elif unknown:
        status = "partial" if len(unknown) < len(pairs) else "unknown"
        score = None
    else:
        status = "complete"
        score = round(sum(pair["score"] for pair in pairs) / len(pairs), 4)
    return {
        "status": status,
        "score": score,
        "pairs": pairs,
        "unknown_pairs": unknown,
        "provenance": "static_service_category_heuristic",
        "is_vendor_collaboration_evidence": False,
    }
