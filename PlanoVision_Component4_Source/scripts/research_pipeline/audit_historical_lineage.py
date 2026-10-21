"""Read-only source audit; writes reports only, never alters original datasets."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.historical_audit import audit_project


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', required=True, help='Fixed YYYY-MM-DD audit date')
    args = parser.parse_args()
    result = audit_project(ROOT, args.as_of)
    target = ROOT / 'reports/historical_lineage_audit.json'
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    eligible = sum(s['technical_split_screen_pass'] for s in result['series'])
    text = f"""# Historical observation lineage audit

Audit date: {args.as_of}. Rule version: {result['audit_version']}.

- Exported observations: {result['rows']} across {result['series_count']} separate series.
- Values and semantic metadata reconciled to cleaned source rows: {result['reconciled_rows']}.
- Open/future calendar-month rows: {result['open_or_future_month_rows']}.
- Source-quality review rows retained in original export: {result['source_quality_review_rows']}.
- Extraction identity/hash errors: {len(result['extraction_identity_errors'])}.
- Cleaned source fields differing from extraction snapshot: {len(result['extraction_content_errors'])}.
- Original inputs preserved: {result['original_inputs_preserved']}.
- Series passing the proposed technical chronology screen: {eligible}.

The screen requires 24 training months and at least six validation and six test
months, a 70/15/15 chronological allocation after excluding open months, no missing
months, unique dates, one unit and reconciled lineage. It is a technical design
proposal, not evidence of forecasting accuracy or approval to train a model.
Quality flags remain visible and require source review before model fitting.

Full row-level issues, series coverage, source hashes and code hash are recorded in
`historical_lineage_audit.json`. No original CSV was overwritten. No simulated
event rows, financial labels or model predictions were generated.

## Limitations and next refinement

""" + '\n'.join('- ' + s for s in result['limitations']) + """

Next: preserve all measurements in a versioned observational export, separate open
months from closed-month experiments, add coverage/quality eligibility and original
publisher locators, and rebuild chronological manifests without imputation. Verify
PDF group context where ambiguity remains. This is separate from the blocked
unitless pilot and LKR calibration tracks. Supervisor review and explicit exact-hash
execution authorization remain required for the synthetic pilot.
"""
    (ROOT / 'reports/historical_lineage_audit.md').write_text(text, encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['rows', 'series_count', 'reconciled_rows',
                                          'open_or_future_month_rows', 'extraction_identity_errors',
                                          'original_inputs_preserved']}))


if __name__ == '__main__':
    main()
