# PP1 evidence: Sri Lankan vendor dataset pilot

**Verified 19 October 2026. Decision: PASS as a small, source-linked data pilot; NOT READY for live Sri Lankan recommendations.** The sample contains ten distinct OpenStreetMap (OSM) mapped business listings. A map listing and a category tag are not confirmation of current operation, event offering, booking availability, price or service area.

## Evidence register

| Check | Observed result | Evidence |
|---|---|---|
| Sample size and identity | 10 rows; 10 distinct vendor IDs, 10 distinct names and 10 nonempty exact OSM URLs | [Sample CSV](../osm_sri_lanka_vendor_sample.csv), [listing evidence table](./listing_evidence.csv) |
| Source-link verification | 10/10 OSM node pages opened on 2026-10-19; each displayed the same node ID, name, craft tag and addr:city as the CSV | [Listing evidence table](./listing_evidence.csv); direct OSM links in each row |
| Source extract | Geofabrik Sri Lanka OSM PBF, HTTP 200, 144,470,045 bytes, SHA-256 3611d4421727b3ea7971a49a01ca32432001453fa2c9a5cd40068162bcfb9f28 at collection | [Collection report](../osm_collection_report.md), [Geofabrik source](https://download.geofabrik.de/asia/sri-lanka.html) |
| Sample file integrity | SHA-256 744E342EA9CF6215934754A4077C507C01DFEFFBE6F4DE494D1DAD5E1E8C8E7A | [Sample CSV](../osm_sri_lanka_vendor_sample.csv) |
| Original template | Still header only; SHA-256 26A1F1DE4C0CCAF44A00C8635E1FA877F4F76CF07FBD601B54DCCA18EBF87BDF | [Original template](../sri_lanka_vendor_profiles.csv) |
| Existing validator | Exit code 0, VALID, 10 rows, 0 errors, 0 warnings | [Actual validator JSON](./validator_result.json), [validator](../validate_sri_lanka_dataset.py) |
| License | OSM data is ODbL licensed with attribution and applicable share-alike obligations | [OSM copyright](https://www.openstreetmap.org/copyright), [pilot attribution](../osm_license_attribution.md) |

**Meaning of “source-linked”:** the OSM elements exist and the displayed names, category tags and cities match this CSV. All ten rows are still marked unverified; no vendor was contacted. The OSM pages can change after this check.

## Category coverage

| Requested category | Sampled listings | Source evidence | Real-world offering |
|---|---:|---|---|
| Photography | 7 | craft=photographer on each linked OSM node | NOT VERIFIED for a specific event |
| Catering | 3 | craft=caterer on each linked OSM node | NOT VERIFIED for a specific event |
| Decoration | 0 | No qualifying sample record | UNKNOWN |
| Entertainment | 0 | No qualifying sample record | UNKNOWN |
| Audio Visual | 0 | No qualifying sample record | UNKNOWN |
| **Total** | **10** | **10/10 source links matched** | **0/10 independently confirmed** |

The zero category rows describe this deliberately small sample, not Sri Lankan market supply. Generic party shops, rental listings and music venues were excluded because their tags do not prove an event decoration, AV or entertainer service. See [tag-selection evidence](../osm_collection_report.md).

## Field completeness and integration gates

| Needed for | Required evidence | Pilot observation | Eligible rows |
|---|---|---|---:|
| Saved Random Forest | stars, review_count, collected_review_count, mean_review_rating, rating_std | All five features missing. The pilot's rating column is blank and is not automatically the model's Yelp stars feature. | **0/10** |
| Existing risk-profile join | business_id, name, rule risk_level and risk_score in the production profile source | vendor_id and vendor_name exist under different names; rule labels/scores absent; current loader does not read pilot | **0/10 direct** |
| Dynamic package options | Distinct service_option_id; joined business_id; supported event types; verified service city/state; capacity applicability; max_guests for Catering; priced unit_price and pricing basis/minima | No option records, quotes, event-type or service-area evidence. Base addr:city is not a service city. | **0/10** |
| Real-world booking claim | Date-specific availability, actual service area, capacity, venue/operational confirmation | All unverified or blank; production simulation does not prove bookings | **0/10** |

All ten records lack **rating, review_count, collected_review_count, mean_review_rating, rating_std, price_lkr, guest_capacity, service_area, availability_status, district and province**. The [field-by-field matrix](./field_gap_matrix.csv) distinguishes fields required by the active code from later real-world verification requirements. Blank is preserved as unknown; no zeros were substituted.

The [active model loader](../../../backend/engine/risk_signals.py) reads only the production Yelp-derived profile file and predicts only complete five-feature rows. The [option loader](../../../backend/engine/package_data_loader.py) reads only production synthetic service options; [candidate selection](../../../backend/engine/candidate_selection.py) requires exact service city/state and event type, plus Catering capacity. Existing ranked packages can carry unknown risk, but these ten profiles have **no priced option rows** and cannot enter that search. The model predicts rule-derived review-risk labels; prior perfect agreement with those rules is not proof of Sri Lankan vendor reliability.

## Three-stage research comparison

| Dimension | Existing US-derived research prototype | Current Sri Lankan pilot | Future Sri Lankan integration requirement |
|---|---|---|---|
| Source data | 18,430 Yelp-derived profiles with historical listing/review fields; 57,549 **synthetic** service options | 10 OSM tagged listings, 7 Photography and 3 Catering; city from addr:city | Permissioned or ODbL-compliant vendor intake with separate provenance for every offering |
| Review-risk model | Saved Random Forest called by existing API on complete Yelp-derived features; labels are rule-derived | 0/10 complete review feature rows; no predictions | Comparable, legitimately sourced review features and out-of-market validation; retain UNKNOWN when unavailable |
| Package generation | Event filtering, bounded combination search, ranking and explanations operate on simulated option data | 0 priced options and no confirmed service coverage; no Sri Lankan package generation | Vendor-confirmed scoped LKR options, event-type support, capacity, service area and explicit identity/currency adapter |
| Location | Exact city/state filtering on simulated US service locations | addr:city is vendor base locality; district/province blank | Reviewed Sri Lankan location model and vendor-confirmed travel area; no automatic base-city-to-service-area assumption |
| Availability and feasibility | Simulation checks plus VERIFICATION_REQUIRED for real-world unknowns | No date-specific availability | Vendor calendars/confirmation and operational evidence before any booking claim |
| PP1 evidence | Philadelphia Wedding scenario previously returned three packages in the [Novelty 1 verification](../../pp1_novelty1_verification/novelty1_verification_report.md); that run was not repeated in this task | Source-linked pilot and validator only | A separately approved, tested Sri Lankan pipeline after data acquisition |

**PP1 message:** demonstrate the existing Philadelphia research prototype as the working system, then present this OSM table as an isolated Sri Lankan market-data feasibility step. Do not describe the ten OSM listings as live recommendations, currently bookable vendors or a trained Sri Lankan model.

## Limits to state aloud

- OSM tags identify mapped places and broad categories; current business status and specific event offerings remain **NOT VERIFIED**.
- No vendor rating, reviews, price, guest capacity, service radius, availability, district or province were inferred.
- The existing 100% model holdout result measures agreement with rule-derived labels, not real-world operational reliability.
- The Philadelphia live demonstration is evidenced by earlier reports, not a new end-to-end rerun in this evidence task. The first live run took about 10.80 seconds, above the five-second proposal target; see [live demo results](../../pp1_final_live_demo_verification/live_demo_results.md).
- OSM-derived redistribution must retain attribution and comply with [ODbL](https://www.openstreetmap.org/copyright).

**Next safe implementation step:** collect vendor-confirmed, scoped LKR service options and service locations with recorded reuse permission in a separate research intake. Review adapter semantics and regression tests before changing production.

