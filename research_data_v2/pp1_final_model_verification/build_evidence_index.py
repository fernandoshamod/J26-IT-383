"""Index audit evidence without touching project sources."""
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIMS = {
    "model_status.md": "Overall verification conclusions and qualifications",
    "model_integration_trace.md": "FastAPI and React source/runtime path",
    "evaluation_metrics.csv": "Reconstructed rule-label holdout metrics",
    "confusion_matrix.png": "Reconstructed rule-label holdout confusion matrix",
    "classification_report.csv": "Per-class reconstructed holdout metrics",
    "feature_importance.png": "Saved model impurity-based feature importances",
    "feature_importance.csv": "Numeric saved model feature importances",
    "prediction_samples.csv": "Direct artifact predictions and probabilities on held-out rows",
    "limitations.md": "Boundaries of model, evaluation, and integration claims",
    "next_actions.md": "PP1 tasks and deferred research claims",
    "fastapi_integration_probe.json": "In-process dynamic endpoint response and direct-model comparison",
    "holdout_details.json": "Reconstructed split counts and class confusion matrix",
    "model_runtime_metadata.json": "Artifact runtime schema, classes, and package metadata",
    "source_hashes.csv": "Before/after SHA-256 for inspected production inputs and source files",
    "verification_log.json": "Audit execution outcomes",
    "verify_model.py": "Reproducible read-only verification procedure",
    "readonly_frontend_probe_server.py": "Read-only compiled frontend and API probe procedure",
    "live_vendor_predictions.png": "Browser view of current API response model classes",
    "model_monitoring_saved_snapshot.png": "Browser view of saved model metric snapshot",
}

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

with (ROOT / "evidence_index.csv").open("w", newline="", encoding="utf-8") as target:
    writer = csv.writer(target)
    writer.writerow(["path", "kind", "supports", "status", "bytes", "sha256", "limitation"])
    for name, claim in CLAIMS.items():
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        status = "RECONSTRUCTED" if name in {"evaluation_metrics.csv", "confusion_matrix.png", "classification_report.csv", "holdout_details.json"} else "OBSERVED"
        limitation = ("Historical held-out IDs were not independently saved; labels are review-rule-derived" if status == "RECONSTRUCTED" else "See limitations.md for the scope of each claim")
        writer.writerow([name, path.suffix.lstrip(".") or "file", claim, status, path.stat().st_size, digest(path), limitation])
    with (ROOT / "source_hashes.csv").open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            path = Path(row["path"])
            writer.writerow([str(path), "source", "Read-only source integrity", "OBSERVED" if row["unchanged"] == "True" else "CHANGED", row["bytes"], digest(path), "Source file; not copied into the audit folder"])
