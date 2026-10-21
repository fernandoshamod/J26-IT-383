# Guest capacity and pricing analysis

## Production rules used

The dynamic path uses [candidate selection](../../backend/engine/candidate_selection.py): exact case-insensitive city/state, exact service category, semicolon-token Corporate support, and `max_guests >= guest_count` **only for Catering**. [Validation](../../backend/engine/validation_helpers.py) prices Catering as `rounded(unit_price_usd × 330.777, 2) × max(guest_count, min_billable_guests)`; Entertainment as `rounded(unit_price_usd × 330.777, 2) × max(duration_hours, min_billable_hours)`, rounded to cents. Non-Catering capacity is **unverified**, not unlimited. The search requires distinct business IDs and total estimated cost ≤ budget. It keeps at most 12 candidates per service and visits at most 5,000 nodes by default; candidate selection mixes low cost and favorable review-rule scores. A package returned for a USER request carries `VERIFICATION_REQUIRED` for availability, scheduling, collaboration, and venue.

**Reproduction inputs:** Corporate; 2027-01-01, 14:00–18:00; LKR 1,000,000; Catering + Entertainment; top_k=10. Date/time were audit assumptions because the scenario description omitted them. The 500-guest catering-only lower bound exceeds budget regardless of event duration.

| Scenario | Service | At location | Corporate | Capacity eligible | Priceable | Individually ≤ budget | Cheapest LKR |
|---|---|---:|---:|---:|---:|---:|---:|
| Bensalem 50 | Catering | 180 (60 vendors) | 180 | 180 (60 vendors) | 180 | 111 | 269,914.00 |
| Bensalem 50 | Entertainment | 6 (2 vendors) | 6 | 6 (capacity not modelled) | 6 | 6 | 198,664.68 |
| Bensalem 500 | Catering | 180 (60 vendors) | 180 | 37 (28 vendors) | 37 | **0** | **2,803,335.00** |
| Bensalem 500 | Entertainment | 6 (2 vendors) | 6 | 6 (capacity not modelled) | 6 | 6 | 198,664.68 |
| Belle Chasse 50 | Catering | 27 (9 vendors) | 27 | 27 (9 vendors) | 27 | 14 | 311,096.00 |
| Belle Chasse 50 | Entertainment | **0** | 0 | 0 | 0 | 0 | — |

Bensalem Catering's 180 option limits are: 50 guests 26, 100 guests 28, 150 guests 33, 200 guests 28, 300 guests 28, and 500 guests 37. These are independently randomized **per option tier**; 37 qualifying options correspond to 28 distinct vendors. The 500-guest Catering minimum uses option `SIMOPT-002318-B`; the 4-hour Entertainment minimum uses `SIMOPT-003950-B`. Those vendors are distinct, but the combined cost is **LKR 3,001,999.68**, over budget by **LKR 2,001,999.68**. Even Catering alone is over budget, so neither candidate truncation nor distinct-vendor conflict can rescue this V1 scenario.

For Bensalem 50, the cheapest observed combination lower bound is **LKR 468,578.68** and its two vendor IDs are distinct. The production run returned 10 ranked packages, so simulated package existence was observed, not inferred from the lower bound. It flagged candidate truncation: 180 Catering options were narrowed to 12; 6 Entertainment options remained. Search visited 78 nodes, evaluated 61 complete combinations, and did not reach the 5,000-node cap. Results are not an exhaustive global ranking or real booking feasibility.

Belle Chasse has no Entertainment option at the exact city/state, so the two-service lower bound is undefined. Catering affordability cannot establish a package. Search visited zero nodes. Neither adding more search nodes nor relaxing ranking would create a missing category; broader service-area evidence or separately justified data would be needed.

The price distribution and all city/state/category counts are in [coverage_by_service.csv](./coverage_by_service.csv) and [coverage_by_location.csv](./coverage_by_location.csv). Option USD prices are illustrative assumptions. The LKR conversion and budget arithmetic therefore diagnose **internal V1 behavior**, not actual market affordability.

