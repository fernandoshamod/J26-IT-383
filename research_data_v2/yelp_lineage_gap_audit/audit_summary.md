# PlanoVision Yelp lineage and Dataset V2 gap audit

**Scope:** read-only inspection of original local Yelp JSONL, current V1 data, source notebook, and production FastAPI rules. Audit run 2026-10-18. No Dataset V2 was generated or integrated. Machine-readable inventory, category/location coverage, and scenario calculations are in [source_inventory.csv](./source_inventory.csv), [coverage_by_service.csv](./coverage_by_service.csv), [coverage_by_location.csv](./coverage_by_location.csv), and [audit_metrics.json](./audit_metrics.json).

## Verified findings

- Original Yelp business and review files were found at `D:\Yelp-JSON (1)\Yelp JSON\yelp_dataset`. The business JSONL has **150,346** records; the review JSONL has **6,990,280** records. The review file was streamed line by line for row count and SHA-256. The 18,430 selected profile IDs all occur in the original business file.
- The current bundle contains **18,430 unique profiles**, **57,549 unique synthetic service options**, **30 simulated event templates**, **191 simulated availability rows**, and **330 simulated collaboration rows**. All option business IDs resolve to profiles. There are **704** represented city/state pairs, but only **54** have both Catering and Entertainment options.
- Direct comparison of selected business records found exact equality for name, city, state, stars, Yelp review_count, open flag, categories, attributes, and hours under the audit parser. Latitude differs in 4,618 rows and longitude in 4,588 at exact floating-point equality; maximum absolute differences are below 0.00000005 degrees and appear to be CSV precision rounding. No difference exceeds 0.000001 degree. This is field equality, not proof of current vendor service capability.
- The existing [review verification table](../../review_summary_verification.csv) contains 18,430 unique IDs and flags all 18,430 count/mean/std checks as matching. Two selected businesses were independently rechecked against the original review stream; details appear in [data_lineage.md](./data_lineage.md). The original extraction code for all profile classification rules was not located, so derivation of every service label remains partly unverified.
- V1 option prices, capacities, event-type support, simulated service areas, setup resources, backup flags, availability, and collaboration outcomes are generated assumptions. They are not vendor quotations, verified limits, or observed bookings.

## Requested scenarios

Reproduction used the production dynamic request path with **2027-01-01, 14:00–18:00 (4 hours)**, Corporate, exact named city/state, LKR 1,000,000, Catering + Entertainment, top 10. The user did not supply a date or duration; time affects Entertainment pricing. It does not change the 500-guest capacity or catering-only budget conclusion. These are simulation outcomes.

| City | Guests | Location/categories | Catering after capacity | Entertainment | Cheapest eligible sum (LKR) | Production result |
|---|---:|---|---:|---:|---:|---|
| Bensalem, PA | 50 | Both present | 180 options / 60 vendors | 6 options / 2 vendors | 468,578.68 | 10 returned; candidate limit reached |
| Bensalem, PA | 500 | Both present | 37 options / 28 vendors | 6 options / 2 vendors | 3,001,999.68 | 0 returned; budget impossible |
| Belle Chasse, LA | 50 | Catering only | 27 options / 9 vendors | 0 | undefined | 0 returned; missing Entertainment |

The 500-guest failure has a **conclusive V1 pricing reason**: the cheapest capacity-eligible Catering option alone costs LKR **2,803,335**, exceeding the entire budget by LKR **1,803,335**. The cheapest Entertainment estimate is LKR **198,664.68**. Their sum is a lower bound, not a real-world quote. Search visited zero nodes because its lower-bound check rejected the request before combination search. The candidate cap was flagged, but did not cause this failure. See [guest_capacity_pricing_analysis.md](./guest_capacity_pricing_analysis.md).

## Feasibility and next step

A versioned Dataset V2 is technically feasible **as a provenance-aware research dataset**. Existing Yelp data can ground business identity, public listing attributes, and review-derived features; it cannot ground event quotations, capacity, date-specific availability, shared crew/equipment, or vendor-pair collaboration. See [dataset_v2_schema_proposal.md](./dataset_v2_schema_proposal.md) and [dataset_v2_build_plan.md](./dataset_v2_build_plan.md). Before PP1, preserve V1, publish the gap audit and independent synthetic scenario definitions, and seek explicitly documented evidence sources. After approval, the next implementation step is an isolated V2 staging pipeline with field-level provenance and unknowns preserved; production integration should await separate review.

## Usage and audit boundary

The local Yelp Dataset User Agreement PDF (dated 2021-02-16) describes academic/noncommercial use, restricts redistribution and commercial/competitive use, and includes a prior review/approval clause for public presentation/publication involving the data or Yelp name. It also addresses summaries/metrics disclosed to third parties with an academic-disclosure exception. Check the actual terms and institutional guidance before public release; this summary is not legal advice. No external data were downloaded. The audit did not establish live business status or real vendor permission. More detail: [source_integrity_report.md](./source_integrity_report.md).

