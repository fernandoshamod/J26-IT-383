"""Read-only reconstruction of the notebook's rule-label holdout split."""

import hashlib
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score,
)
from sklearn.model_selection import train_test_split

from backend.engine.risk_signals import FEATURES, MODEL_FILE, verified_model

ROOT = Path(__file__).resolve().parents[1]
TRAINING_FILE = ROOT / "data/cleaned/vendor_profiles_missingness_checked.csv"
PROFILE_FILE = ROOT / "hybrid_simulation_v1/real_vendor_profiles.csv"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_model():
    columns = ["business_id", *FEATURES, "risk_level"]
    checked = pd.read_csv(TRAINING_FILE, usecols=columns)
    profiles = pd.read_csv(PROFILE_FILE, usecols=columns)
    identity_verified = checked.equals(profiles)
    if not identity_verified:
        return {"status": "unverified_original_source",
                "reason": "Training source and current profile rows differ; held-out split not reproducible."}
    if checked[list(FEATURES)].isna().any().any() or checked["risk_level"].isna().any():
        return {"status": "unverified_missing_features",
                "reason": "Original notebook split has missing features or labels."}
    model = verified_model()
    x_train, x_test, y_train, y_test = train_test_split(
        checked[list(FEATURES)], checked["risk_level"],
        test_size=0.20, random_state=42, stratify=checked["risk_level"])
    labels = list(model.classes_)
    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, labels=labels,
                                   output_dict=True, zero_division=0)
    return {
        "status": "reconstructed_notebook_holdout",
        "source": str(TRAINING_FILE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(TRAINING_FILE),
        "model_sha256": sha256(MODEL_FILE),
        "source_profile_rows_equal": identity_verified,
        "split_method": "sklearn train_test_split(test_size=0.20, random_state=42, stratify=y)",
        "train_count": len(x_train), "test_count": len(x_test),
        "features": list(FEATURES), "classes": labels,
        "class_support": {label: int(report[label]["support"]) for label in labels},
        "accuracy": accuracy_score(y_test, predictions),
        "macro_precision": precision_score(y_test, predictions, average="macro", zero_division=0),
        "macro_recall": recall_score(y_test, predictions, average="macro", zero_division=0),
        "macro_f1": f1_score(y_test, predictions, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_test, predictions, average="weighted", zero_division=0),
        "per_class": {
            label: {metric: report[label][metric] for metric in ("precision", "recall", "f1-score", "support")}
            for label in labels},
        "confusion_matrix_labels": labels,
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "label_origin": "deterministic_review_feature_rules",
        "independent_real_world_validation": False,
        "caution": "The target was generated using related review features; excellent accuracy measures rule imitation, not real-world failure prediction.",
    }
