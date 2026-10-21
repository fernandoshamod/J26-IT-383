
from fastapi import APIRouter
from backend.engine.package_data_loader import load_package_data

router = APIRouter(prefix="/api/locations", tags=["Locations"])

@router.get("")
def get_supported_locations():
    _, options = load_package_data()

    locations = (
        options[
            ["simulated_service_city", "simulated_service_state"]
        ]
        .dropna()
        .drop_duplicates()
        .sort_values(
            ["simulated_service_city", "simulated_service_state"]
        )
    )

    return {
        "data_origin": "synthetic_simulation",
        "locations": [
            {
                "city": row["simulated_service_city"],
                "state": row["simulated_service_state"]
            }
            for _, row in locations.iterrows()
        ]
    }
