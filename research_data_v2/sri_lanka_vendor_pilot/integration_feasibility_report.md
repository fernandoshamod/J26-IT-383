# Recommendation engine compatibility audit

## Current interfaces inspected

- [Request schema](../../backend/schemas/dynamic_package_request.py): event_type, date/time, city, state, guest_count, budget_lkr, required_services and top_k. Five pilot categories are accepted request services.
- [Service option loader](../../backend/engine/package_data_loader.py): reads the production synthetic service option CSV, requiring service_option_id, business_id, service_category, simulated_service_city/state, supported_event_types, max_guests, unit_price, pricing_basis, min billable guests/hours, capacity applicability, data_origin and is_vendor_confirmed. It transforms USD unit_price to LKR using a fixed rate.
- [Candidate selection](../../backend/engine/candidate_selection.py): exact service category, exact city and state, supported event type, and catering guest capacity. A pilot vendor base city is not proof of a service city.
- [Risk signals](../../backend/engine/risk_signals.py): loads only the existing production profile CSV and a hash-checked saved Random Forest. It uses five ordered numeric features: stars, review_count, collected_review_count, mean_review_rating and rating_std. It expects business_id, name, risk_level and risk_score in its existing profile source, and predicts only complete feature rows.

## Field mapping and gaps

| Pilot field | Production relationship | Gap or restriction |
|---|---|---|
| vendor_id, vendor_name | Could map to business_id, name in a future adapter | Current loader never reads this pilot; IDs must be unique in a separate namespace. |
| service_category | Same labels for the five target categories | Category evidence must show the actual service, not just a generic retail category. |
| city, district, province, country | Existing request uses city and state; options use simulated_service_city/state | Province/district cannot silently be treated as a US state; base city does not establish service area. |
| rating, review_count, mean_review_rating, rating_std, collected_review_count | Potentially map rating → stars and four same-named features | All five must be present, numeric and comparable to original feature definitions. Current pilot has 0 rows; future rows with missing features cannot receive an evidence-based model prediction. |
| price_lkr, guest_capacity | Related to unit_price_lkr and max_guests | A vendor-level price/capacity is not a priced option with pricing_basis, billable minima and event scope. Do not infer option rows from these alone. |
| service_area, availability_status | Could support future filtering | Current selector has no flexible travel-area or verified availability logic. Blank means unknown, not eligible or available. |
| source fields, verification_status, data_type | Valuable provenance | No equivalent per-field provenance in current ranking contract. Preserve outside production until an approved integration design exists. |

## Model and integration verdict

The **saved Random Forest cannot be used on this header-only CSV**, and a future vendor without all five review features cannot be scored. Even with complete features, out-of-market data would require feature-definition and distribution checks before interpreting predictions. The model predicts **rule-derived review-risk labels**, not independently established real-world reliability. Do not fill missing review features with zero or infer risk from a website card.

There is **no current direct integration path** from the pilot CSV to package generation. Integration would require a versioned import/adapter, genuinely priced service-option evidence, explicit service location/event support, identity and currency handling, an unknown-risk path, and regression tests. Strict location filtering is safest for evidence-based recommendations but will yield no match when service coverage is unknown. Flexible filtering requires vendor-confirmed service areas and travel rules. A clearly labeled simulation-only demonstration could explore broader locations, but must not represent them as live availability or production results. No such production behavior has been changed.

**Current pilot model-eligible vendors: 0/0. Current package-eligible vendors: 0/0.** These are counts from the empty template, not an assessment of the Sri Lankan market.

