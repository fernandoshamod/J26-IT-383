# Sri Lankan vendor pilot data dictionary

CSV: [sri_lanka_vendor_profiles.csv](./sri_lanka_vendor_profiles.csv). Exactly 21 columns, one row per distinct vendor assigned to one evidence-supported service category in this pilot. Empty CSV cells mean **unknown/not supplied**; zero is a measured numeric value, never a substitute for missing. No records have been collected yet.

| Column | Meaning and permitted representation |
|---|---|
| vendor_id | Stable pilot identifier; for OSM use element type plus ID such as osm_node_123, preserving the element URL. Required and unique. |
| vendor_name | Name exactly as given by the permitted source; required. |
| service_category | One of Photography, Decoration, Catering, Entertainment, Audio Visual. Use only with specific source evidence for that category. |
| city | Vendor base city/locality when explicitly recorded. Does not imply travel radius. |
| district | Sri Lankan administrative district if supported by source or separately documented geocoding. |
| province | Sri Lankan province if supported by source or separately documented geocoding. |
| country | Sri Lanka or LK; required for populated rows. |
| rating | Published numeric rating, 0–5, only if source provenance and interpretation are clear; otherwise blank. |
| review_count | Published nonnegative count tied to that rating; otherwise blank. |
| mean_review_rating | Mean calculated from legitimately collected, attributable review ratings; otherwise blank. |
| rating_std | Standard deviation calculated from the same collected ratings, 0–5; otherwise blank. |
| collected_review_count | Number of collected ratings used for the mean/std; otherwise blank. Not interchangeable with a listing's review_count. |
| price_lkr | Vendor-confirmed numeric quote in LKR for a defined service scope; otherwise blank. A generic web article, price band or currency symbol is not a quote. |
| guest_capacity | Confirmed maximum guests for the specific service option, if applicable; otherwise blank. |
| service_area | Explicitly stated coverage area, ideally structured later; blank if only an address/base city is known. |
| availability_status | Leave blank unless date-specific evidence can be represented and traced in a future schema. “Open now” is not event availability. |
| source_name | Name of licensed/permission-granted source, such as OpenStreetMap; required. |
| source_url | Exact HTTPS URL of the vendor record or OSM element; required. |
| collected_at | ISO 8601 timestamp with timezone of collection; required. |
| verification_status | unverified, vendor_confirmed, or source_confirmed; required. A website listing alone is unverified. |
| data_type | licensed_open_data, vendor_submitted, permission_based_export, or synthetic. Real-world record counts exclude synthetic. |

**Provenance note:** A real public listing means the listing exists, not that its service offerings, price, booking availability, or identity have been independently verified. For an OSM record, category mapping from an OSM tag is a derived interpretation of open mapped data. A future version should add a per-field evidence ledger and permission/license reference; this 21-column pilot schema cannot express per-field proof.


