"""
Cleaning and normalisation of historical event records (proposal Section
3.3: "cleaning and normalisation of historical records, resolution of
inconsistent activity naming ... feature extraction for the duration
prediction model").

This module knows nothing about how the records were produced — it works
the same on the synthetic history (history_generation.py) and on real
exported records from the industry partner. Every rule here is one a
human could check by hand, and every row it changes or drops is counted
in a CleaningReport so the cleaning is auditable, not silent.

Rules:
  1. Activity names -> one canonical name per activity type, via an
     explicit alias table (normalise case/punctuation first, then look
     up). Unknown names are DROPPED and counted, never guessed.
  2. Impossible durations are DROPPED: actual <= 0, or actual more than
     MAX_ACTUAL_TO_PLANNED_RATIO times the planned duration (a typo such
     as an extra zero). Not "fixed" — we can't know the true value.
  3. Missing values (guest count, travel distance) are KEPT as missing.
     XGBoost learns a default direction for missing values at every split
     (Chen & Guestrin, 2016, "sparsity-aware split finding"), so imputing
     a made-up number would only add noise. The linear baseline, which
     cannot handle missing values, imputes the training median itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

MAX_ACTUAL_TO_PLANNED_RATIO = 4.0

# Normalised alias -> canonical activity type. Built by listing the
# distinct raw names in the export and mapping each one by hand — the same
# thing a data analyst would do with a real export.
ACTIVITY_ALIASES = {
    "venue setup": "venue_setup", "venue set up": "venue_setup", "setup venue": "venue_setup",
    "decor": "decor", "floral decor": "decor", "decoration": "decor", "decor install": "decor",
    "sound check": "sound_check", "soundcheck": "sound_check", "av check": "sound_check",
    "catering load in": "catering_load_in", "catering loadin": "catering_load_in",
    "food load in": "catering_load_in",
    "guest arrival": "guest_arrival", "guests arriving": "guest_arrival", "welcome": "guest_arrival",
    "ceremony": "ceremony", "poruwa ceremony": "ceremony", "main ceremony": "ceremony",
    "photos": "photos", "photography": "photos", "photo session": "photos", "photo shoot": "photos",
    "dinner service": "dinner_service", "dinner": "dinner_service", "buffet service": "dinner_service",
    "speeches": "speeches", "speech": "speeches", "toasts": "speeches", "speeches toasts": "speeches",
    "entertainment": "entertainment", "band": "entertainment", "dj set": "entertainment",
    "dancing": "entertainment",
    "strike": "strike", "load out": "strike", "breakdown": "strike", "strike load out": "strike",
}


def normalise_name(raw: str) -> str:
    """'Catering Load-in' / 'catering_loadin' -> 'catering load in' / 'catering loadin'."""
    text = re.sub(r"[^a-z0-9]+", " ", str(raw).lower())
    return " ".join(text.split())


def canonical_activity(raw: str) -> str | None:
    return ACTIVITY_ALIASES.get(normalise_name(raw))


@dataclass
class CleaningReport:
    rows_in: int = 0
    names_renamed: int = 0
    dropped_unknown_name: int = 0
    dropped_impossible_duration: int = 0
    missing_values_kept: dict[str, int] = field(default_factory=dict)
    rows_out: int = 0

    def lines(self) -> list[str]:
        out = [
            f"rows in:                         {self.rows_in}",
            f"activity names normalised:       {self.names_renamed}",
            f"dropped (unknown activity name): {self.dropped_unknown_name}",
            f"dropped (impossible duration):   {self.dropped_impossible_duration}",
        ]
        for column, count in self.missing_values_kept.items():
            out.append(f"missing {column + ' (kept as NaN):':<24} {count}")
        out.append(f"rows out:                        {self.rows_out}")
        return out


def _canonicalise_names(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    canonical = df["activity_name"].map(canonical_activity)
    report.names_renamed = int((canonical.notna() & (canonical != df["activity_name"])).sum())
    report.dropped_unknown_name = int(canonical.isna().sum())
    df = df.assign(activity_type=canonical).dropna(subset=["activity_type"])
    return df.drop(columns=["activity_name"])


def clean_activity_records(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    report = CleaningReport(rows_in=len(raw))
    df = _canonicalise_names(raw.copy(), report)

    impossible = (df["actual_duration_minutes"] <= 0) | (
        df["actual_duration_minutes"] > MAX_ACTUAL_TO_PLANNED_RATIO * df["planned_duration_minutes"]
    )
    report.dropped_impossible_duration = int(impossible.sum())
    df = df[~impossible]

    report.missing_values_kept = {"guest_count": int(df["guest_count"].isna().sum())}
    report.rows_out = len(df)
    return df.reset_index(drop=True), report


def clean_arrival_records(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    report = CleaningReport(rows_in=len(raw))
    df = _canonicalise_names(raw.copy(), report)
    df = df[df["lateness_minutes"] >= 0]
    report.missing_values_kept = {
        "travel_distance_km": int(df["travel_distance_km"].isna().sum()),
        # Missing by design for a vendor's first-ever job (no history yet).
        "vendor_prior_mean_lateness": int(df["vendor_prior_mean_lateness"].isna().sum()),
    }
    report.rows_out = len(df)
    return df.reset_index(drop=True), report
