# Pilot validation report (19 October 2026)

## Actual validation

Command run from project root:

```powershell
& 'd:/Vendor-Intelligence-System/venv/Scripts/python.exe' -B 'research_data_v2/sri_lanka_vendor_pilot/validate_sri_lanka_dataset.py'
```

Result: exit code **0**, status **TEMPLATE_ONLY**, exact 21-column header accepted, **0 data rows**, **0 declared real rows**, **0 errors**, **0 warnings**. VS Code Problems reported no diagnostics for the validator. This is a structural pass for an empty template, **not** validation of any Sri Lankan vendor records or of license permission.

| Target category | Collected | Target | Gap |
|---|---:|---:|---:|
| Photography | 0 | 20 | 20 |
| Decoration | 0 | 20 | 20 |
| Catering | 0 | 20 | 20 |
| Entertainment | 0 | 20 | 20 |
| Audio Visual | 0 | 20 | 20 |
| **Total** | **0** | **100** | **100** |

Because there are no rows, missing-field counts are empty; this does **not** mean future records contain complete fields. Ratings, published and collected review counts, review mean/std, LKR price, guest capacity, service area and event availability are all **not available for any collected vendor**. Duplicate IDs/names and location consistency could not be assessed on real pilot records.

The validator checks duplicate normalized IDs/names, required fields, category vocabulary, country, numeric ranges and types, city and district/province completeness, provenance URL shape, data labels, unknown availability warnings and ISO 8601 timestamps. It checks format and internal consistency; it cannot establish whether a website granted reuse permission or whether a vendor's claim is true. Manual provenance and license review remain mandatory before importing records.

A separate temporary negative fixture was run after an initial inline-command quoting error. The successful fixture run exited 0 and asserted that invalid rating, duplicate vendor ID, malformed source URL and missing city were detected; the validator returned **FAIL with 8 errors and 2 warnings** for that intentionally bad input. The temporary fixture was removed after the check.


