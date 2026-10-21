# Import-ready research data schema

The eight header-only files in [schemas/](./schemas/) are **templates, not data**. No sample rows are represented as facts. Externally sourced entity rows should include `source_record_id`, `source_uri`, `observed_at_utc`, `license_or_permission`, `evidence_class` (REAL_PUBLIC, DERIVED, SYNTHETIC_TEST, UNKNOWN), and `provenance_id` where relevant. The data_provenance entity stores source-level metadata instead. Importers must reject unknown enum values and keep raw source IDs. Numeric missing values remain blank/null, never zero by default. Event quotations and availability need a vendor-confirmed timestamp to be considered verified.

| Entity | Primary key | Important fields / constraints | Foreign keys |
|---|---|---|---|
| vendors | vendor_id | source_system, source_record_id, name, service taxonomy, address/location, rating/review count and observation date; rating cannot prove reliability | provenance_id |
| vendor_service_options | option_id | vendor_id, category, pricing_basis, currency, unit_price, min billing, capacity, coverage; price needs price_evidence_status and valid period | vendor_id, provenance_id |
| vendor_availability | availability_id | vendor_id, date/time interval with timezone, status, checked_at, confirmation status; unknown is valid | vendor_id, provenance_id |
| vendor_resource_requirements | requirement_id | option_id, resource_type, quantity, unit, setup/teardown duration, evidence class | option_id, provenance_id |
| vendor_pair_evidence | pair_evidence_id | two **distinct** vendor IDs, evidence_type, event context, outcome/unknown, timestamp and verification status; category scores do not populate this table | vendor_a_id, vendor_b_id, provenance_id |
| event_scenarios | scenario_id | event type, date/interval/timezone, city/state, guest count, budget/currency, required services; synthetic scenarios explicitly tagged | provenance_id |
| conflict_test_cases | case_id | scenario_id, selected option IDs, conflict type, expected outcome, evidence/reference and adjudicator; label origin explicit | scenario_id, provenance_id |
| data_provenance | provenance_id | source title/URI, acquisition timestamp, source file SHA-256, license, transformation, reviewer, limitations | none |

**Validation rules:** IDs are nonblank unique within an entity; foreign keys must resolve; timestamps use ISO 8601 with timezone for real evidence; money uses decimal and explicit currency; positive quantity/capacity where known; `UNKNOWN` cannot be converted to false or compatible. Preserve raw and normalized values separately. Cross-source business matching requires an adjudicated link table in a later task. Historical synthetic `SIMEVT-*` availability and collaboration records never apply to new `USER-*` events.

**Import plan:** Stage lawful extracts in a new isolated directory, hash them, map fields into these templates, validate constraints and license, produce a row-level provenance report, and only then consider controlled experiments. This audit performs no import into the application.

## Staging helper

[stage_research_csv.ps1](./stage_research_csv.ps1) is an **unexecuted** import-ready helper. From this audit folder, use `./stage_research_csv.ps1 -Entity vendors -InputCsv <prepared-file.csv>` only after source permissions and identity mapping are reviewed. It requires the exact header-only template columns, unique nonblank keys, a canonical evidence class, and public source URI/license evidence before copying data into this audit folder's `staged_imports/` directory with a source hash manifest. It refuses an existing destination. This is a first-stage structural check, not full semantic, license or cross-table validation. No public data was imported in Task 1.
