
"""JSON-safe serialization for PlanoVision API responses."""

import math
from datetime import date, datetime

import numpy as np
import pandas as pd


def to_json_safe(value):
    """
    Convert nested values into JSON-compatible Python types.

    Missing and non-finite values become None (JSON null).
    The original input is not modified.
    """

    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, np.generic):
        return to_json_safe(value.item())

    if isinstance(value, pd.DataFrame):
        return [
            to_json_safe(row)
            for row in value.to_dict("records")
        ]

    if isinstance(value, pd.Series):
        return to_json_safe(value.to_dict())

    if isinstance(value, dict):
        return {
            str(key): to_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, np.ndarray)):
        return [
            to_json_safe(item)
            for item in value
        ]

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, (str, int, bool)):
        return value

    raise TypeError(
        f"Unsupported JSON value type: {type(value).__name__}"
    )
