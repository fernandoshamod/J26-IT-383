# PP1-safe recommendations

## Before PP1

1. Freeze and report V1, including source hashes, category/location coverage, and the three scenario results. Present all prices and capacities as simulation inputs.
2. Define evaluation scenarios independently of generator output. Record event date/time, budget, currency and exchange rate, guest band, categories, exact location, and expected **internal filter reason**. Mark real-world feasibility UNKNOWN.
3. Recover the original selection/classification rules and independently verify review aggregates by streaming. Document the local Yelp agreement and obtain institutional guidance before public release of source-derived metrics.
4. Keep the 500-guest and Belle Chasse gaps explicit. The cheapest 500-guest Catering option in Bensalem is LKR 2,803,335, exceeding the entire budget; the two-service bound is LKR 3,001,999.68. Belle Chasse has zero Entertainment options. Search expansion alone cannot fix either.
5. Clearly separate the static category score from vendor-pair evidence. The 15 heuristic matrix rows and 330 random simulated collaboration rows are not proof of actual cooperation.

## After PP1 and separate approval

Build the isolated versioned V2 staging tables; obtain evidence-backed capacity, quotation, service radius, availability, resource and venue records; adjudicate real collaboration/outcomes; then consider algorithm or frontend integration. Do not retrain a real failure predictor on random conflicts or review-rule risk labels.

## Direct improvement paths

- **500 guests:** seek verified catering capacity and dated quotations. V1's random caps and illustrative per-person USD prices can support a sensitivity experiment, not a market claim. Multi-caterer composition would require an independently specified algorithm and coordination evidence.
- **Service categories and locations:** inspect false-negative classification rules; confirm actual event offerings and service radii; distinguish source business address from delivery area. Entertainment has 154 vendors across 55 city/state pairs and Audio Visual 12 across 8, versus Catering's 16,145 across 665.
- **Actual compatibility:** require named vendors, shared event/time, roles, documented outcome, consent/source, and independent verification. Resource compatibility additionally needs crew/equipment inventories and interval assignments.
- **Fair comparison:** freeze scenario inputs, budget/currency/rate, date/time, common vendor cohort, search bounds and top_k. Report common-cohort quality and expanded-cohort coverage separately. Stratify by guest band, location, and category. Track unknowns, abstentions, simulated feasibility, independent real labels, latency, and provenance. Split by vendor/pair/event to avoid leakage.

**Recommended next implementation step after findings approval:** build an isolated V2 staging pipeline with field-level provenance and explicit unknown values. Do not integrate it into production until separately reviewed.
