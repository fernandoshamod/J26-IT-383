# Report Generator

## Actual implementation

The PDF is generated in the browser by `frontend/src/services/pdfReports.js`, imported by `frontend/src/pages/AdminWorkspace.jsx`. The previous implementation used a minimal hand-built PDF stream: every line was placed at a fixed coordinate, each line was truncated to 110 characters, and there was no table, wrapping, page-break or footer model. That caused the limitations sentence to run beyond the right margin and produced a plain-text-looking document.

## Current implementation

The replacement generator produces a real PDF document with:

- PlanoVision teal branding and report header.
- Report title, subtitle and timestamp.
- Ivory/white/teal visual system.
- Metric cards and structured tables.
- Word wrapping inside the content margin.
- Automatic page breaks and continuation headers.
- Footer page numbering.
- Separate Vendor Intelligence, Event Management and Model Evaluation content layouts.
- Numeric formatting: accuracy `100.00%`, Macro F1 `1.0000`, test records `3,686`.
- Explicit research limitations and synthetic-data disclosures.

The frontend download link now retains its object URL for five seconds, which also avoids revoking the URL before the browser has begun the download. New filenames include a date, for example `planovision-model-report-2026-10-20.pdf`.

## Verified files

The latest files were downloaded and opened from the browser Downloads folder, then copied into this evidence folder as:

- `verified-download-vendor-report.pdf`
- `verified-download-events-report.pdf`
- `verified-download-model-report.pdf`

All three opened in the browser PDF viewer. The model report visibly showed `100.00%`, `1.0000` and `3,686`.
