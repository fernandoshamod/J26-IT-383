"""Verified model inference and profile joins for rule-derived vendor risk."""

from functools import lru_cache
import hashlib
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROFILE_FILE = ROOT / "hybrid_simulation_v1" / "real_vendor_profiles.csv"
MODEL_FILE = ROOT / "models" / "vendor_risk_random_forest.pkl"
MODEL_SHA256 = "4eed156cfdf677b992b8c36350c21c968d7cb4d532a8afd302ca1b697aea3e6a"
FEATURES = (
    "stars", "review_count", "collected_review_count",
    "mean_review_rating", "rating_std",
)
CLASSES = ("High", "Low", "Medium")


class RiskModelUnavailable(RuntimeError):
    """The verified local model cannot be used for inference."""


@lru_cache(maxsize=1)
def _load_verified_model(digest):
    try:
        package = joblib.load(MODEL_FILE)
        model = package["model"]
        if (
            list(package["features"]) != list(FEATURES)
            or list(model.feature_names_in_) != list(FEATURES)
            or tuple(model.classes_) != CLASSES
            or list(package["classes"]) != list(CLASSES)
            or package["target"] != "risk_level"
            or package["label_type"] != "rule-derived"
        ):
            raise RiskModelUnavailable("Risk model metadata does not match verified features and labels")
        return model
    except (OSError, KeyError, TypeError, AttributeError, ValueError) as exc:
        raise RiskModelUnavailable(f"Cannot load verified risk model: {exc}") from exc


def verified_model():
    try:
        digest = hashlib.sha256(MODEL_FILE.read_bytes()).hexdigest()
    except OSError as exc:
        raise RiskModelUnavailable(f"Risk model artifact unavailable: {exc}") from exc
    if digest != MODEL_SHA256:
        raise RiskModelUnavailable(
            "Risk model artifact hash changed; verify the new artifact before inference"
        )
    return _load_verified_model(digest)


def load_risk_signals(business_ids):
    """Match unique profile IDs and predict only rows with complete model inputs."""
    model = verified_model()
    columns = ["business_id", "name", *FEATURES, "risk_level", "risk_score"]
    try:
        profiles = pd.read_csv(PROFILE_FILE, usecols=columns)
    except (OSError, ValueError) as exc:
        raise RiskModelUnavailable(f"Vendor profile data unavailable: {exc}") from exc
    requested = {str(value) for value in business_ids}
    matched = profiles.loc[profiles["business_id"].astype(str).isin(requested)].copy()
    duplicate_ids = set(
        matched.loc[matched["business_id"].duplicated(keep=False), "business_id"]
        .astype(str)
    )
    unique = matched.loc[~matched["business_id"].astype(str).isin(duplicate_ids)]
    lookup = {
        business_id: {
            "vendor_id": business_id,
            "vendor_name": None,
            "predicted_risk_level": None,
            "rule_risk_level": None,
            "rule_risk_score": None,
            "risk_status": "profile_not_found",
            "risk_provenance": "unknown",
        }
        for business_id in requested
    }
    for business_id in duplicate_ids:
        lookup[business_id]["risk_status"] = "ambiguous_profile_id"

    complete = unique.loc[unique[list(FEATURES)].notna().all(axis=1)]
    predictions = model.predict(complete[list(FEATURES)]) if not complete.empty else []
    for (_, row), prediction in zip(complete.iterrows(), predictions):
        business_id = str(row["business_id"])
        score = row["risk_score"]
        label = row["risk_level"]
        signal = lookup[business_id]
        signal["vendor_name"] = str(row["name"]) if pd.notna(row["name"]) else None
        signal["predicted_risk_level"] = str(prediction)
        signal["rule_risk_level"] = str(label) if pd.notna(label) else None
        signal["risk_provenance"] = "random_forest_prediction_of_rule_generated_label"
        if pd.isna(score) or not 0 <= float(score) <= 100:
            signal["risk_status"] = "missing_rule_risk_score"
        elif prediction != label:
            signal["risk_status"] = "model_rule_disagreement"
        else:
            signal["rule_risk_score"] = float(score)
            signal["risk_status"] = "available"

    incomplete = unique.loc[~unique[list(FEATURES)].notna().all(axis=1)]
    for _, row in incomplete.iterrows():
        business_id = str(row["business_id"])
        lookup[business_id]["risk_status"] = "missing_model_features"
        lookup[business_id]["vendor_name"] = (
            str(row["name"]) if pd.notna(row["name"]) else None
        )
    counts = pd.Series([signal["risk_status"] for signal in lookup.values()]).value_counts()
    return lookup, {
        "model_artifact": "models/vendor_risk_random_forest.pkl",
        "model_sha256": MODEL_SHA256,
        "model_features": list(FEATURES),
        "label_origin": "rule_generated_from_review_features",
        "independent_real_world_validation": False,
        "requested_vendor_ids": len(requested),
        "status_counts": {str(key): int(value) for key, value in counts.items()},
    }
