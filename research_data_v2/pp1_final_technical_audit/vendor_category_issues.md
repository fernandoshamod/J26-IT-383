# Vendor service-category correctness audit

## Assignment path

[build_hybrid_dataset.py](../../build_hybrid_dataset.py) reads [vendor_recommendation_dataset_ids_checked.csv](../../vendor_recommendation_dataset_ids_checked.csv), splits each profile's semicolon-separated `service_categories`, and creates three Basic/Standard/Premium options per vendor-service pair. The current [synthetic_service_options.csv](../../hybrid_simulation_v1/synthetic_service_options.csv) contains 57,549 rows, representing 19,183 pairs. At request time, [candidate_selection.py](../../backend/engine/candidate_selection.py) matches the option's `service_category` **exactly** to the requested service and filters simulated city/state, event type and Catering capacity. It does not revalidate the vendor's original Yelp category or confirm a real service offering. [package_data_loader.py](../../backend/engine/package_data_loader.py) loads the existing rows.

The earlier [lineage audit](../yelp_lineage_gap_audit/data_lineage.md) verified original Yelp business attributes/categories for selected IDs and found no complete original script for assigning the profile `service_categories`. Thus the profile service label is **DERIVED / partly UNKNOWN**, and the option is **SYNTHETIC_TEST**.

## Focused source-support check

A read-only pass over 18,430 [real_vendor_profiles.csv](../../hybrid_simulation_v1/real_vendor_profiles.csv) rows found these vendor-service counts: Catering 16,145; Photography 467; Decoration 882; Entertainment 154; Audio Visual 12; Equipment Rental 184; Event Planning 1,339 (total 19,183). Every assigned service had at least one corresponding `matched_categories` marker under this **audit-defined conservative mapping**: Catering `Caterers` or `Caters=True`; Photography `Photographers`, `Event Photography` or `Videographers`; Decoration `Florists`, `Floral Designers` or `Balloon Services`; Entertainment `DJs`, `Musicians` or `Party Characters`; Audio Visual `Audio/Visual Equipment Rental`; Equipment Rental `Party Equipment Rentals` or `Audio/Visual Equipment Rental`; Event Planning `Party & Event Planning` or `Wedding Planning`. **Zero pairs lacked such a marker.** This check is not a reconstruction of the missing original classification script and does not prove current service capability.

## Visible review candidates

| Vendor / ID | Assigned service | Original public category evidence | Assessment |
|---|---|---|---|
| Trader Joe's / `mzTTdvQGkUHZ8ii7OnZC5w` | Decoration | `Florists`, `Flowers & Gifts`, `Grocery`, `Shopping`; `matched_categories=Florists` | Broad florist tag supports a category inference, but no verified event-decoration package or installation service. **SERVICE OFFERING NOT_VERIFIED**; likely poor demo example. |
| matt-hair / `_GameVII8zP9Ymtr7OePgQ` | Photography | `Photographers`, `Session Photography`, plus hair/beauty categories; `matched_categories=Photographers` | Photography tag exists, so a hard false assignment is **NOT_VERIFIED**. Event photography availability/scope is unknown. |
| Minibooths / `FQ_QUyrwtnaEdxUxruZkXg` | Photography | `Photo Booth Rentals`, `Event Photography`, `Photographers` | Clearer category-level example, still not a confirmed quotation or booking. |
| Petit Jardin En Ville / `_t_UwNkwAinJSljDDYvnoQ` | Decoration | `Florists`, `Flowers & Gifts`, `Wedding Planning` | Category-level match only; exact decoration offering unknown. |

These values are from [real_vendor_profiles.csv](../../hybrid_simulation_v1/real_vendor_profiles.csv), whose source business fields were compared to original Yelp records in [audit_summary.md](../yelp_lineage_gap_audit/audit_summary.md). The prior [Vendor Intelligence capture](../pp1_final_model_verification/live_vendor_predictions.png) shows the first two questionable rows.

**Conclusion:** No clear source-category contradiction was proven for the 19,183 pair labels under the conservative marker check. The actual correctness gap is the leap from broad Yelp tags or `Caters=True` to specific event-service options. In particular, 15,475 of the 16,145 Catering profiles carry the `Caters=True` marker, which does not establish quoted 50- or 500-guest event capacity. Real vendor offerings, dates, prices and limits remain **NOT_VERIFIED**.

**P1 action:** Review the exact vendors shown in the PP1 demo and disclose source-category inference. After PP1, trace/rebuild the original mapping with field-level evidence and explicit unknowns; do not silently label questionable options as confirmed.
