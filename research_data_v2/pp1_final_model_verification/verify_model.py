"""Read-only verification of the saved PP1 Random Forest and ASGI path."""
import csv
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ["MPLBACKEND"] = "Agg"
os.environ["MPLCONFIGDIR"] = str(OUT / "matplotlib_config")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score, recall_score)
from sklearn.model_selection import train_test_split
from backend.engine.risk_signals import FEATURES, MODEL_FILE, MODEL_SHA256, PROFILE_FILE, verified_model
from research_evaluation.model_audit import TRAINING_FILE

def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def save_csv(name, rows, fields=None):
    with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

paths = [
    MODEL_FILE, TRAINING_FILE, PROFILE_FILE,
    ROOT / "notebooks/01_vendor_dataset_audit.ipynb",
    ROOT / "backend/engine/risk_signals.py",
    ROOT / "research_evaluation/model_audit.py",
    ROOT / "backend/engine/dynamic_package_service.py",
    ROOT / "backend/engine/bounded_package_generator.py",
    ROOT / "backend/api/packages.py",
    ROOT / "backend/main.py",
    ROOT / "frontend/src/App.jsx",
    ROOT / "frontend/src/pages/AdminPages.jsx",
    ROOT / "frontend/src/pages/PackageViews.jsx",
    ROOT / "frontend/src/services/api.js",
    ROOT / "frontend/src/data/evaluation_summary.json",
]
source_rows = [{"path": str(path), "bytes": path.stat().st_size, "sha256_before": digest(path)}
               for path in paths]
assert source_rows[0]["sha256_before"] == MODEL_SHA256

package = joblib.load(MODEL_FILE)
model = verified_model()
features = list(FEATURES)
classes = list(model.classes_)
assert package["model"].__class__.__name__ == "RandomForestClassifier"
assert package["features"] == features == list(model.feature_names_in_)
assert package["classes"] == classes
assert package["target"] == "risk_level" and package["label_type"] == "rule-derived"

columns = ["business_id", *features, "risk_level"]
training = pd.read_csv(TRAINING_FILE, usecols=columns, dtype={"business_id": "string"})
profiles = pd.read_csv(PROFILE_FILE, usecols=columns, dtype={"business_id": "string"})
same_ordered_input = training.equals(profiles)
complete = not training[features + ["risk_level"]].isna().any().any()
rule = np.select([
    training["mean_review_rating"].ge(4) &
    training["rating_std"].lt(1) &
    training["collected_review_count"].ge(20),
    training["mean_review_rating"].ge(3),
], ["Low", "Medium"], default="High")
rule_agreement = int(np.sum(rule == training["risk_level"].to_numpy()))
rule_disagreements = len(training) - rule_agreement

meta = {
    "model_file": str(MODEL_FILE),
    "model_sha256": source_rows[0]["sha256_before"],
    "model_type": type(model).__name__,
    "sklearn_version_runtime": sklearn.__version__,
    "python_version_runtime": sys.version,
    "n_estimators": model.n_estimators,
    "n_features_in": int(model.n_features_in_),
    "features_in_order": features,
    "classes_in_order": classes,
    "package_target": package["target"],
    "package_label_type": package["label_type"],
    "training_rows": len(training),
    "training_profile_rows_equal_in_order": bool(same_ordered_input),
    "complete_features_and_label": bool(complete),
    "rule_label_agreement_rows": rule_agreement,
    "rule_label_disagreement_rows": rule_disagreements,
    "original_holdout_ids_persisted": False,
}
(OUT / "model_runtime_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

if not same_ordered_input or not complete:
    save_csv("evaluation_metrics.csv", [{"metric": "holdout_reconstruction", "value": "NOT_VERIFIED",
                                         "scope": "ordered source mismatch or missing features"}])
else:
    X_train, X_test, y_train, y_test = train_test_split(
        training[features], training["risk_level"], test_size=0.20,
        random_state=42, stratify=training["risk_level"])
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)
    report = classification_report(y_test, pred, labels=classes,
                                   output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, pred, labels=classes)
    metrics = [
        ("training_rows", len(X_train)),
        ("test_rows", len(X_test)),
        ("accuracy", accuracy_score(y_test, pred)),
        ("balanced_accuracy", balanced_accuracy_score(y_test, pred)),
        ("macro_precision", precision_score(y_test, pred, average="macro", zero_division=0)),
        ("macro_recall", recall_score(y_test, pred, average="macro", zero_division=0)),
        ("macro_f1", f1_score(y_test, pred, average="macro", zero_division=0)),
        ("weighted_f1", f1_score(y_test, pred, average="weighted", zero_division=0)),
        ("rule_label_agreement_all_rows", rule_agreement / len(training)),
    ]
    save_csv("evaluation_metrics.csv",
             [{"metric": key, "value": value,
               "scope": "reconstructed notebook holdout vs deterministic review-derived labels"}
              for key, value in metrics])
    save_csv("classification_report.csv",
             [{"class": key, "precision": values.get("precision"),
               "recall": values.get("recall"), "f1_score": values.get("f1-score"),
               "support": values.get("support")}
              for key, values in report.items() if isinstance(values, dict)])
    samples = []
    for label in classes:
        chosen = [i for i, actual in enumerate(y_test.to_numpy()) if actual == label][:10]
        for i in chosen:
            source_index = int(X_test.index[i])
            row = training.iloc[source_index]
            sample = {"source_row_index_0based": source_index,
                      "business_id": str(row.business_id),
                      "true_rule_label": str(y_test.iloc[i]),
                      "predicted_model_label": str(pred[i]),
                      "correct_vs_rule_label": bool(pred[i] == y_test.iloc[i])}
            sample.update({name: float(row[name]) for name in features})
            sample.update({f"probability_{name}": float(proba[i, j])
                           for j, name in enumerate(classes)})
            samples.append(sample)
    save_csv("prediction_samples.csv", samples)
    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    image = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(classes)), classes)
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Predicted rule-derived class")
    ax.set_ylabel("Held-out rule-derived class")
    ax.set_title("Reconstructed notebook holdout")
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(OUT / "confusion_matrix.png", dpi=170)
    plt.close(fig)
    importance = [{"feature": name, "importance": float(value)}
                  for name, value in zip(features, model.feature_importances_)]
    save_csv("feature_importance.csv", importance)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh([item["feature"] for item in importance],
            [item["importance"] for item in importance])
    ax.invert_yaxis()
    ax.set_xlabel("Random Forest impurity importance")
    ax.set_title("Saved artifact feature importance")
    fig.tight_layout()
    fig.savefig(OUT / "feature_importance.png", dpi=170)
    plt.close(fig)
    (OUT / "holdout_details.json").write_text(json.dumps({
        "split_recipe": "train_test_split(test_size=0.20, random_state=42, stratify=y)",
        "source_file": str(TRAINING_FILE),
        "source_sha256": digest(TRAINING_FILE),
        "train_count": len(X_train), "test_count": len(X_test),
        "classes": classes, "confusion_matrix_rows_true_columns_predicted": cm.tolist(),
        "original_heldout_ids_saved": False,
        "interpretation": "Reconstructed holdout, not an independent failure-outcome test."
    }, indent=2), encoding="utf-8")

# Exercise the actual FastAPI route in-process, without starting or changing a server.
try:
    from fastapi.testclient import TestClient
    from backend.main import app
    payload = {
        "event_type": "Corporate", "event_date": "2027-01-01",
        "start_time": "14:00", "end_time": "18:00",
        "city": "Bensalem", "state": "PA", "guest_count": 50,
        "budget_lkr": 1000000,
        "required_services": ["Catering", "Entertainment"], "top_k": 3,
    }
    with TestClient(app) as client:
        response = client.post("/api/packages/generate-dynamic", json=payload)
    result = response.json()
    integration = {
        "method": "FastAPI TestClient POST /api/packages/generate-dynamic",
        "request": payload, "http_status": response.status_code,
        "generation_status": result.get("generation", {}).get("status"),
        "model_sha256_in_response": result.get("risk_data_audit", {}).get("model_sha256"),
        "risk_data_audit": result.get("risk_data_audit"),
        "package_count": len(result.get("generation", {}).get("packages", [])),
        "sample_package_vendor_signals": [],
    }
    for pkg in result.get("generation", {}).get("packages", [])[:1]:
        for signal in pkg.get("risk", {}).get("vendors", []):
            integration["sample_package_vendor_signals"].append({
                key: signal.get(key) for key in
                ["vendor_id", "predicted_risk_level", "rule_risk_level",
                 "risk_status", "risk_provenance"]})
    if response.status_code == 200:
        ids = [row["vendor_id"] for row in integration["sample_package_vendor_signals"]]
        matched = profiles.loc[profiles.business_id.astype(str).isin(ids)]
        direct = {str(row.business_id): str(label)
                  for (_, row), label in zip(matched.iterrows(), model.predict(matched[features]))}
        integration["response_predictions_match_direct_model"] = all(
            direct.get(row["vendor_id"]) == row["predicted_risk_level"]
            for row in integration["sample_package_vendor_signals"])
    (OUT / "fastapi_integration_probe.json").write_text(
        json.dumps(integration, indent=2), encoding="utf-8")
except Exception as exc:
    (OUT / "fastapi_integration_probe.json").write_text(
        json.dumps({"status": "NOT_VERIFIED", "error_type": type(exc).__name__,
                    "error": str(exc)}, indent=2), encoding="utf-8")

for row in source_rows:
    row["sha256_after"] = digest(row["path"])
    row["unchanged"] = row["sha256_before"] == row["sha256_after"]
save_csv("source_hashes.csv", source_rows)
summary = {"all_source_hashes_unchanged": all(row["unchanged"] for row in source_rows),
           "model_sha256_matches_production_pin": source_rows[0]["sha256_before"] == MODEL_SHA256,
           "training_profile_rows_equal": same_ordered_input,
           "rule_label_disagreements": rule_disagreements,
           "model_features": features, "classes": classes}
(OUT / "verification_log.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))

