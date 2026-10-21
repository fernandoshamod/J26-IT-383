# Source inventory and integrity

[Source inventory](./source_inventory.csv) records absolute paths, byte sizes, CSV/JSONL row counts, schemas, and SHA-256 for **25** inspected source, data, code, manifest, notebook, and agreement files. Hashes were computed by bounded 4 MiB reads; the 5.34 GB Yelp review file was streamed line by line. No source JSONL file was loaded into memory. The original Yelp files found were:

| File | Bytes | Rows | SHA-256 |
|---|---:|---:|---|
| `yelp_academic_dataset_business.json` | 118,863,795 | 150,346 | See inventory |
| `yelp_academic_dataset_review.json` | 5,341,868,833 | 6,990,280 | See inventory |

The same folder also contains Yelp checkin, tip, user files and a 9.29 GB extensionless `yelp_dataset` file. They were not used in the traced V1 path and were not hashed. An Office lock file was ignored. The local `Dataset_User_Agreement.pdf` is inventoried and hashed. Its extracted text is dated 2021-02-16. It limits the stated license to academic/noncommercial purposes, bars commercial/competitive use and broad redistribution/display, restricts third-party disclosure of data summaries or metrics except necessary academic disclosure, and calls for Yelp review/approval before public academic presentation/publication involving data or its name. It also states a 12-month term and termination provisions. The present research use and any planned public publication should be reviewed against the full agreement and institutional guidance; this is not legal advice.

**Integrity checks:** original Yelp business IDs matched all 18,430 current profile IDs; current profile IDs are unique; all 57,549 option IDs are unique; every option business ID resolves to a profile; no profile lacks an option. The manifest declares seed 42 and the source CSV hash. Compare its `source_sha256` with the actual CSV hash in the inventory before rerunning any builder. No independent checksum manifest was available for the original Yelp files, so their authenticity relative to Yelp's distribution cannot be proven from local files alone.

The current audit folder already contained a zero-byte `test.tmp` before this work. It was left untouched. An audit-only `write_probe.txt` was created while testing the output-folder write path; it contains no source data. No production source, dataset, model, configuration, or frontend file was intentionally edited. This integrity statement covers inventoried file content and observed actions; it is not a filesystem-wide before/after snapshot.



## Hash comparison

The actual SHA-256 of `vendor_recommendation_dataset_ids_checked.csv` is `47d380f2972eb9377610c7587b246835cdd0475492ee9518be6044b9e354d392`, exactly matching `dataset_manifest.json.source_sha256`. Original Yelp business SHA-256: `392280627d83ecdcbff8006bba5db289f8436ef147d5a103b1ace5b54186727f`. Original Yelp review SHA-256: `a4edc050d14eec25373a75e7ee211d42f49f14f47230837d8c7849eb9c5f2f96`. These are local integrity fingerprints, not publisher-authentication signatures.


## Post-audit verification

A second SHA-256 pass over all 25 inventoried inputs after report generation found **zero mismatches**. All 11 requested deliverables are present and nonempty; both coverage CSVs parse (7 service rows and 704 location rows), the scenario metrics JSON parses, and every relative Markdown link in the audit reports resolves. The project source-code files in the inventory therefore have identical bytes before and after the reporting phase. No production code, dataset, model, configuration, or frontend edit was made.
