
"""Load synthetic event and service-option data for PlanoVision."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIMULATION_DIR = PROJECT_ROOT / "hybrid_simulation_v1"

EVENT_FILE = SIMULATION_DIR / "synthetic_event_requirements.csv"
OPTION_FILE = SIMULATION_DIR / "synthetic_service_options.csv"

USD_TO_LKR = 330.777
EXCHANGE_RATE_DATE = "2026-10-13"


def load_package_data():
    """Load datasets and reproduce notebook LKR transformations."""

    if not EVENT_FILE.is_file():
        raise FileNotFoundError(f"Event dataset not found: {EVENT_FILE}")

    if not OPTION_FILE.is_file():
        raise FileNotFoundError(f"Option dataset not found: {OPTION_FILE}")

    events = pd.read_csv(EVENT_FILE)
    options = pd.read_csv(OPTION_FILE)

    required_event_columns = {
        "event_id",
        "event_type",
        "city",
        "state",
        "guest_count",
        "budget",
        "required_services"
    }

    required_option_columns = {
        "business_id",
        "service_category",
        "simulated_service_city",
        "simulated_service_state",
        "supported_event_types",
        "max_guests",
        "unit_price"
    }

    missing_event_columns = required_event_columns - set(events.columns)
    missing_option_columns = required_option_columns - set(options.columns)

    if missing_event_columns:
        raise ValueError(
            f"Missing event columns: {sorted(missing_event_columns)}"
        )

    if missing_option_columns:
        raise ValueError(
            f"Missing option columns: {sorted(missing_option_columns)}"
        )

    events_lkr = events.copy()
    options_lkr = options.copy()

    options_lkr["unit_price_lkr"] = (
        options_lkr["unit_price"] * USD_TO_LKR
    ).round(2)

    events_lkr["budget_lkr"] = (
        events_lkr["budget"] * USD_TO_LKR
    ).round(2)

    options_lkr["display_currency"] = "LKR"
    events_lkr["display_currency"] = "LKR"

    return events_lkr, options_lkr


def load_service_options():
    """Load current synthetic service options without requiring a sample event."""
    if not OPTION_FILE.is_file():
        raise FileNotFoundError(f"Option dataset not found: {OPTION_FILE}")
    options = pd.read_csv(OPTION_FILE)
    required = {
        "service_option_id", "business_id", "service_category",
        "simulated_service_city", "simulated_service_state",
        "supported_event_types", "max_guests", "unit_price",
        "pricing_basis", "min_billable_guests", "min_billable_hours",
        "guest_capacity_applicability", "data_origin", "is_vendor_confirmed",
    }
    missing = required - set(options.columns)
    if missing:
        raise ValueError(f"Missing option columns: {sorted(missing)}")
    options["unit_price_lkr"] = (options["unit_price"] * USD_TO_LKR).round(2)
    options["display_currency"] = "LKR"
    return options