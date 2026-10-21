"""Standalone PP1 vendor-pair evidence and operational conflict proof of concept.

This module does not import PlanoVision production code or load saved packages.
All bundled observations are SYNTHETIC_TEST. Results describe only supplied
pair/operational evidence; venue suitability is always external and pending.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from itertools import combinations
from math import isfinite
from typing import Any

COMPATIBLE = "COMPATIBLE_WITH_EVIDENCE"
CONFLICT = "CONFLICT_WITH_EVIDENCE"
PENDING = "VERIFICATION_REQUIRED"
ALLOWED_CLASSES = {"REAL_PUBLIC", "DERIVED", "SYNTHETIC_TEST", "UNKNOWN"}
PAIR_TYPES = {"direct_pair_observation", "simulated_pair_observation"}


def _when(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Intervals require explicit timezone offsets")
    return parsed


def _overlap(a_start: datetime, a_end: datetime,
             b_start: datetime, b_end: datetime) -> bool:
    """Half-open intervals: touching endpoints do not overlap."""
    return a_start < b_end and b_start < a_end


def _pair_key(first: str, second: str) -> tuple[str, str]:
    if not first or not second or first == second:
        raise ValueError("Pair lookup requires two distinct nonblank vendor IDs")
    return tuple(sorted((first, second)))


def _usable_pair_record(record: dict[str, Any], event_id: str) -> bool:
    if record.get("evidence_type") not in PAIR_TYPES:
        return False  # Category rules cannot prove named-vendor collaboration.
    origin = record.get("evidence_class")
    if origin not in ALLOWED_CLASSES:
        raise ValueError("Invalid evidence_class")
    if record.get("event_id") != event_id:
        return False  # Never borrow another sample event's pair result.
    if not record.get("source") or not record.get("observed_at_utc"):
        return False
    _when(record["observed_at_utc"])
    if origin == "SYNTHETIC_TEST":
        return (record.get("verification_status") == "simulated"
                and record.get("evidence_type") == "simulated_pair_observation")
    if origin == "REAL_PUBLIC":
        return (record.get("verification_status") == "verified"
                and record.get("evidence_type") == "direct_pair_observation"
                and bool(record.get("source_uri")))
    return False


def lookup_pair(vendor_a: str, vendor_b: str, event_id: str,
                records: list[dict[str, Any]]) -> dict[str, Any]:
    """Symmetric lookup; contradictory or unverified evidence stays pending."""
    key = _pair_key(vendor_a, vendor_b)
    matches: list[dict[str, Any]] = []
    rejected = 0
    for record in records:
        try:
            record_key = _pair_key(str(record.get("vendor_a_id", "")),
                                   str(record.get("vendor_b_id", "")))
        except ValueError:
            rejected += 1
            continue
        if record_key != key:
            continue
        if _usable_pair_record(record, event_id):
            matches.append(record)
        else:
            rejected += 1
    outcomes = {row.get("outcome") for row in matches}
    if outcomes == {"compatible"}:
        status, reason = COMPATIBLE, "Explicit pair evidence supports compatibility within its recorded scope."
    elif outcomes == {"conflict"}:
        status, reason = CONFLICT, "Explicit pair evidence records a conflict within its recorded scope."
    elif len(outcomes) > 1:
        status, reason = PENDING, "Pair evidence contradicts itself; adjudication is required."
    else:
        status, reason = PENDING, "No usable event-specific pair evidence; collaboration is unknown."
    return {
        "vendor_ids": list(key), "status": status, "reason": reason,
        "evidence_ids": sorted(str(row["evidence_id"]) for row in matches),
        "evidence_classes": sorted({str(row["evidence_class"]) for row in matches}),
        "sources": sorted({str(row["source"]) for row in matches}),
        "observed_at_utc": sorted({str(row["observed_at_utc"]) for row in matches}),
        "rejected_or_out_of_scope_records": rejected,
        "is_real_world_collaboration_confirmed": False,
    }


def _availability_covers(record: dict[str, Any],
                         start: datetime, end: datetime) -> bool:
    """Require source timestamp and interval covering this assignment."""
    try:
        _when(record["observed_at_utc"])
        return _when(record["start_at"]) <= start and end <= _when(record["end_at"])
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate supplied assignments and evidence; never infer missing facts."""
    event = case["event"]
    event_id = str(event["event_id"])
    event_start, event_end = _when(event["start_at"]), _when(event["end_at"])
    if event_end <= event_start:
        raise ValueError("Event end must follow start")
    assignments = case["assignments"]
    if not assignments:
        raise ValueError("At least one assignment is required")
    checks: list[dict[str, Any]] = []
    windows: list[tuple[datetime, datetime, datetime, datetime]] = []

    def add(code: str, status: str, message: str, origin: str) -> None:
        checks.append({"code": code, "status": status, "message": message,
                       "evidence_class": origin})

    option_ids: set[str] = set()
    for item in assignments:
        option_id = str(item.get("option_id", "")).strip()
        vendor_id = str(item.get("vendor_id", "")).strip()
        if not option_id or option_id in option_ids or not vendor_id:
            raise ValueError("Assignments need unique nonblank option IDs and vendor IDs")
        option_ids.add(option_id)
        start, end = _when(item["service_start"]), _when(item["service_end"])
        if not (event_start <= start < end <= event_end):
            raise ValueError("Service intervals must lie within the submitted event")
        setup = item.get("setup_minutes")
        teardown = item.get("teardown_minutes")
        if setup is not None and (not isinstance(setup, (int, float)) or
                                  not isfinite(setup) or setup < 0):
            raise ValueError("Invalid setup duration")
        if teardown is not None and (not isinstance(teardown, (int, float)) or
                                     not isfinite(teardown) or teardown < 0):
            raise ValueError("Invalid teardown duration")
        occupation_start = start - timedelta(minutes=setup or 0)
        occupation_end = end + timedelta(minutes=teardown or 0)
        windows.append((start, end, occupation_start, occupation_end))
        availability = item.get("availability")
        if (not availability or availability.get("event_id") != event_id
                or availability.get("evidence_class") not in {"SYNTHETIC_TEST", "REAL_PUBLIC"}
                or not availability.get("source")
                or not _availability_covers(availability, start, end)):
            add(f"availability:{option_id}", PENDING,
                f"{option_id}: event-specific availability is unknown.", "UNKNOWN")
        elif (availability["evidence_class"] == "REAL_PUBLIC"
              and availability.get("verification_status") != "verified"):
            add(f"availability:{option_id}", PENDING,
                f"{option_id}: public availability evidence is not vendor-confirmed.", "UNKNOWN")
        elif availability.get("status") == "unavailable":
            add(f"availability:{option_id}", CONFLICT,
                f"{option_id}: supplied event-specific evidence says unavailable.",
                availability["evidence_class"])
        elif availability.get("status") == "available":
            add(f"availability:{option_id}", COMPATIBLE,
                f"{option_id}: availability is supported only within supplied evidence scope.",
                availability["evidence_class"])
        else:
            add(f"availability:{option_id}", PENDING,
                f"{option_id}: availability is unknown.", "UNKNOWN")

    pair_results = []
    vendors = sorted({str(item["vendor_id"]) for item in assignments})
    for first, second in combinations(vendors, 2):
        pair = lookup_pair(first, second, event_id, case.get("pair_evidence", []))
        pair_results.append(pair)
        add(f"vendor_pair:{first}:{second}", pair["status"], pair["reason"],
            "SYNTHETIC_TEST" if pair["evidence_classes"] == ["SYNTHETIC_TEST"] else
            "REAL_PUBLIC" if pair["evidence_classes"] == ["REAL_PUBLIC"] else "UNKNOWN")

    for i, j in combinations(range(len(assignments)), 2):
        left, right = assignments[i], assignments[j]
        if left["vendor_id"] != right["vendor_id"]:
            continue
        label = f"{left['option_id']}:{right['option_id']}"
        if any(item.get(field) is None for item in (left, right)
               for field in ("setup_minutes", "teardown_minutes")):
            add(f"schedule_evidence:{left['option_id']}:{right['option_id']}", PENDING,
                "Same-vendor setup or teardown duration is unknown.", "UNKNOWN")
        a_start, a_end, a_occ_start, a_occ_end = windows[i]
        b_start, b_end, b_occ_start, b_occ_end = windows[j]
        if _overlap(a_start, a_end, b_start, b_end):
            flags = (left.get("can_multitask"), right.get("can_multitask"))
            if flags == (True, True):
                add(f"same_vendor_service:{label}", COMPATIBLE,
                    "Both assignments explicitly support simultaneous service.", "SYNTHETIC_TEST")
            elif False in flags:
                add(f"same_vendor_service:{label}", CONFLICT,
                    "Same vendor has overlapping service intervals and a documented single-task constraint.",
                    "SYNTHETIC_TEST")
            else:
                add(f"same_vendor_service:{label}", PENDING,
                    "Same vendor has overlapping services; staffing capacity is unknown.", "UNKNOWN")
        if _overlap(a_occ_start, a_occ_end, b_occ_start, b_occ_end):
            flags = (left.get("exclusive_setup_crew"), right.get("exclusive_setup_crew"))
            if flags == (True, True):
                add(f"setup_teardown:{label}", CONFLICT,
                    "Same vendor's setup/service/teardown windows overlap with an exclusive crew.",
                    "SYNTHETIC_TEST")
            elif None in flags:
                add(f"setup_teardown:{label}", PENDING,
                    "Setup/teardown windows overlap but crew exclusivity is unknown.", "UNKNOWN")

    limits = case.get("resource_limits", {})
    resource_uses: dict[str, list[tuple[datetime, datetime, float]]] = defaultdict(list)
    for item, (_, _, occ_start, occ_end) in zip(assignments, windows):
        for resource in item.get("resources", []):
            resource_id = str(resource.get("resource_id", ""))
            quantity = resource.get("quantity")
            if not resource_id.startswith(("equipment:", "crew:")):
                raise ValueError("Only vendor equipment/crew resources are in this engine")
            if (not isinstance(quantity, (int, float)) or not isfinite(quantity)
                    or quantity <= 0):
                raise ValueError("Resource quantities must be positive and finite")
            resource_uses[resource_id].append((occ_start, occ_end, float(quantity)))
    for resource_id in sorted(resource_uses):
        limit = limits.get(resource_id)
        capacity = limit.get("capacity") if isinstance(limit, dict) else None
        if (capacity is None or not isinstance(capacity, (int, float))
                or not isfinite(capacity) or capacity < 0
                or not limit.get("source")
                or limit.get("evidence_class") not in {"SYNTHETIC_TEST", "REAL_PUBLIC"}):
            add(f"resource:{resource_id}", PENDING,
                f"{resource_id}: documented resource capacity is missing.", "UNKNOWN")
            continue
        endpoints = []
        for start, end, quantity in resource_uses[resource_id]:
            endpoints.extend(((start, quantity), (end, -quantity)))
        endpoints.sort(key=lambda value: (value[0], value[1]))
        demand = peak = 0.0
        for _, delta in endpoints:
            demand += delta
            peak = max(peak, demand)
        if peak > capacity:
            add(f"resource:{resource_id}", CONFLICT,
                f"{resource_id}: peak demand {peak:g} exceeds documented limit {capacity:g}.",
                limit["evidence_class"])
        else:
            add(f"resource:{resource_id}", COMPATIBLE,
                f"{resource_id}: peak demand {peak:g} fits documented limit {capacity:g}.",
                limit["evidence_class"])

    status = (CONFLICT if any(row["status"] == CONFLICT for row in checks)
              else PENDING if any(row["status"] == PENDING for row in checks)
              else COMPATIBLE)
    failed = [row["message"] for row in checks if row["status"] == CONFLICT]
    pending = [row["message"] for row in checks if row["status"] == PENDING]
    return {
        "case_id": case["case_id"], "event_id": event_id,
        "status": status, "checks": checks, "pair_results": pair_results,
        "conflict_count": len(failed), "pending_count": len(pending),
        "explanation": (failed if failed else pending if pending else
                        ["No conflict found within the supplied vendor-pair and operational evidence."]),
        "venue_suitability": PENDING,
        "venue_explanation": "External Venue Suitability / Digital Twin evidence is not evaluated here.",
        "evidence_scope": "SYNTHETIC_TEST fixture; no real-world availability or collaboration confirmed.",
        "is_real_world_feasible": False,
    }
