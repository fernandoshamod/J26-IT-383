
"""Event-specific candidate selection for PlanoVision."""

import pandas as pd


def select_candidates_for_event(
    selected_event,
    selected_services,
    options_lkr
):
    """
    Select service options using the original notebook rules.

    Returns:
        dict[str, pandas.DataFrame]
    """

    candidate_groups = {}

    for service in selected_services:

        group = options_lkr.loc[
            options_lkr["service_category"].eq(service)
            &
            options_lkr["simulated_service_city"]
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq(str(selected_event["city"]).strip().casefold())
            &
            options_lkr["simulated_service_state"]
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq(str(selected_event["state"]).strip().casefold())
            &
            options_lkr["supported_event_types"]
            .fillna("")
            .apply(
                lambda value:
                str(selected_event["event_type"]).strip().casefold()
                in [
                    x.strip().casefold()
                    for x in str(value).split(";")
                ]
            )
            &
            (
                options_lkr["service_category"].ne("Catering")
                |
                options_lkr["max_guests"].ge(
                    selected_event["guest_count"]
                )
            )
        ].copy()

        candidate_groups[service] = group

    return candidate_groups
