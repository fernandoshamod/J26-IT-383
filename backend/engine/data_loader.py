"""Load PlanoVision synthetic feasibility evidence."""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIMULATION_DIR = PROJECT_ROOT / "hybrid_simulation_v1"

AVAILABILITY_FILE = (
    SIMULATION_DIR / "synthetic_availability.csv"
)

COLLABORATION_FILE = (
    SIMULATION_DIR / "synthetic_collaboration_scenarios.csv"
)

AVAILABILITY_COLUMNS = [
    "event_id",
    "business_id",
    "event_date",
    "availability_status",
    "checked_interval_start",
    "checked_interval_end",
    "data_origin",
    "is_vendor_confirmed",
    "generation_version",
]

COLLABORATION_COLUMNS = [
    "simulated_collaboration_id",
    "event_id",
    "pair_id",
    "vendor_a_id",
    "vendor_b_id",
    "simulated_conflict",
    "outcome_origin",
    "data_origin",
    "is_actual_collaboration",
    "pair_group_split",
    "generation_version",
]


def _load_checked_csv(path, expected_columns):
    if not path.is_file():
        raise FileNotFoundError(
            f"Required simulation file not found: {path}"
        )

    df = pd.read_csv(path)

    if list(df.columns) != expected_columns:
        raise ValueError(
            f"Unexpected CSV schema: {path.name}"
        )

    return df


def load_feasibility_data():
    """Return availability and collaboration DataFrames."""

    availability = _load_checked_csv(
        AVAILABILITY_FILE,
        AVAILABILITY_COLUMNS,
    )

    collaboration = _load_checked_csv(
        COLLABORATION_FILE,
        COLLABORATION_COLUMNS,
    )

    return availability, collaboration
