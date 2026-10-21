"""Isolated candidate-filter prototype; production modules remain unchanged.

Reuses one request-local location/event-type mask across selected services.
No cache, package storage, changed limits, or altered scoring.
"""


def select_candidates_once(selected_event, selected_services, options_lkr):
    city = str(selected_event["city"]).strip().casefold()
    state = str(selected_event["state"]).strip().casefold()
    event_type = str(selected_event["event_type"]).strip().casefold()
    shared = (
        options_lkr["simulated_service_city"].astype(str).str.strip().str.casefold().eq(city)
        & options_lkr["simulated_service_state"].astype(str).str.strip().str.casefold().eq(state)
        & options_lkr["supported_event_types"].fillna("").apply(
            lambda value: event_type in [x.strip().casefold()
                                         for x in str(value).split(";")]
        )
    )
    candidates = {}
    for service in selected_services:
        mask = (
            shared
            & options_lkr["service_category"].eq(service)
            & (
                options_lkr["service_category"].ne("Catering")
                | options_lkr["max_guests"].ge(selected_event["guest_count"])
            )
        )
        candidates[service] = options_lkr.loc[mask].copy()
    return candidates