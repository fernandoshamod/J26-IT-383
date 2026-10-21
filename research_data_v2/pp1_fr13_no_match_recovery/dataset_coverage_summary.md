# Source-backed coverage diagnostics

The new reusable function is [coverage_diagnostics.py](../../backend/engine/coverage_diagnostics.py). It runs only after a zero-package dynamic response, using the same loaded option rows, event-type/location normalization, Catering capacity rule and LKR pricing validator as candidate generation. It adds no keystroke-triggered scans and returns aggregate counts only.

For each required service it reports source, location, event-type, capacity-eligible, priceable and individually affordable counts plus a minimum observed eligible LKR price. It also reports location rows, whether combination search started, category-rule candidate removals (always 0 because the matrix is not a filter), a package price lower bound only if every required service has a priceable option, and up to five source-supported alternative cities. Suggested cities have priceable options for each requested category under the same event-type/capacity/pricing rules; distinct vendors, combined budget, feasibility and bounded search may still prevent a package. No location is changed automatically.

| Controlled request | Source rows | Location rows | Required service | Priceable | Individually affordable at LKR 1m |
|---|---:|---:|---|---:|---:|
| Corporate, Belle Chasse LA, 50 guests | 57,549 | 27 | Entertainment | 0 | 0 |
| Same | 57,549 | 27 | Catering | 27 | 14 |

The observed first five alternative locations with priceable options for both categories were Belleville IL, Bensalem PA, Berlin NJ, Blackwood NJ and Boise ID. This list is a synthetic option coverage observation, not a booking recommendation. In a separate successful Bensalem request at the same budget, eligible candidate counts were Entertainment 6 and Catering 180; top 3 packages were returned. At LKR 1 in Bensalem, the observed per-category minimum-price sum was **LKR 667,243.36**, a necessary lower bound rather than a guaranteed package quotation. See [scenario JSON](./demo_test_results.json).

Cause vocabulary: NO_LOCATION_COVERAGE, NO_SERVICE_COVERAGE, UNPRICEABLE_OPTIONS, BUDGET_INSUFFICIENT, NO_COMPATIBLE_COMBINATION, SEARCH_LIMIT_REACHED and UNKNOWN_CAUSE are produced only when supported by stage/search evidence. Pydantic invalid requests remain HTTP 422; unexpected backend errors remain errors, not valid zero-result diagnostics. Multiple reasons may coexist. A candidate cap without any search does not establish SEARCH_LIMIT_REACHED.

All prices/service areas are SYNTHETIC_TEST simulation data. The returned provenance fields explicitly state synthetic_simulation, unverified availability and no vendor confirmation.