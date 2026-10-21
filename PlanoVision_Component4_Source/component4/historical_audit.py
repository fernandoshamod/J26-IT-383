"""Source reconciliation for historical observations. No simulation or model fitting."""
from collections import defaultdict
import csv
from datetime import date
import hashlib
import math
from pathlib import Path

VERSION = 'historical-lineage-audit.0.1'


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def month_number(value):
    d = date.fromisoformat(value)
    if d.day != 1:
        raise ValueError('Monthly dates must be canonical month starts')
    return d.year * 12 + d.month - 1


def reconcile(rows, inflation, retail, as_of):
    """Audit exported values against cleaned source rows, without deleting observations.

    A closed calendar month is not proof of complete publisher coverage. A separate
    report marks missing source weeks, ambiguous group names and source quality flags.
    """
    cutoff = month_number(date.fromisoformat(as_of).replace(day=1).isoformat())
    sources = {}
    for kind, records in [('inflation', inflation), ('retail', retail)]:
        for record in records:
            rid = record['source_record_id']
            if not rid or rid in sources:
                raise ValueError('Missing or duplicate source record identity')
            sources[rid] = (kind, record)
    issues, metrics, series = [], [], defaultdict(list)
    keys = set()
    for number, row in enumerate(rows, 2):
        reasons = []
        key = (row.get('series_id'), row.get('ds'))
        if key in keys:
            reasons.append('duplicate_series_date')
        keys.add(key)
        try:
            period = month_number(row['ds'])
            if period >= cutoff:
                reasons.append('open_or_future_calendar_month')
        except (KeyError, ValueError, TypeError):
            period = None
            reasons.append('invalid_month_date')
        try:
            value = float(row['y'])
            if not math.isfinite(value) or value <= 0:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            value = None
            reasons.append('invalid_measurement')
        refs = row.get('provenance', '').split(';')
        if not all(refs) or len(refs) != len(set(refs)):
            reasons.append('missing_or_repeated_lineage')
        found = [sources[r] for r in refs if r in sources]
        if len(found) != len(refs):
            reasons.append('unknown_source_record')
        expected = None
        source_quality = False
        if found and len(found) == len(refs):
            kinds = {k for k, _ in found}
            records = [r for _, r in found]
            source_quality = any(r.get('quality_flag', '') for r in records)
            try:
                if kinds == {'inflation'} and len(records) == 1:
                    r = records[0]
                    expected = float(r['index_value'])
                    metadata = (row['ds'] == r['month'] and
                                row['series_id'] == f"{r['source_id']}:{r['index_type']}:base{r['base_year']}" and
                                row['source_id'] == r['source_id'] and
                                row['unit'] == f"index (base {r['base_year']})" and
                                row['observation_kind'] == 'observed_monthly_index' and
                                row['cost_category'] == 'inflation_index')
                    if not metadata:
                        reasons.append('index_metadata_mismatch')
                elif kinds == {'retail'}:
                    r = records[0]
                    dates = {f"{int(s['year']):04d}-{int(s['month']):02d}-01" for s in records}
                    items = {(s['item_raw'], s['unit_raw'], s['source_id']) for s in records}
                    weeks = [s['reported_week'] for s in records]
                    expected = math.fsum(float(s['current_price_lkr']) for s in records) / len(records)
                    metadata = (dates == {row['ds']} and len(items) == 1 and
                                row['series_id'] == f"S003:{r['item_raw']}:{r['unit_raw']}" and
                                row['unit'] == f"LKR/{r['unit_raw']}" and row['source_id'] == 'S003' and
                                row['cost_category'] == 'ingredient_price_proxy' and
                                row['observation_kind'] == 'monthly mean of published weekly prices')
                    if not metadata:
                        reasons.append('retail_metadata_mismatch')
                    if len(set(weeks)) != len(weeks):
                        reasons.append('duplicate_week_in_mean')
                    if float(row.get('reported_weeks', '')) != len(set(weeks)):
                        reasons.append('reported_week_count_mismatch')
                    if any(s['parse_status'] != 'Parsed' or not s['unit_raw'] or
                           float(s['current_price_lkr']) <= 0 for s in records):
                        reasons.append('ineligible_retail_source')
                else:
                    reasons.append('mixed_or_invalid_source_kinds')
            except (KeyError, ValueError, TypeError):
                reasons.append('invalid_source_measurement_or_metadata')
        if expected is not None and value is not None and not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-8):
            reasons.append('source_value_mismatch')
        hard = [r for r in reasons if r != 'open_or_future_calendar_month']
        metrics.append({'csv_row': number, 'series_id': key[0], 'ds': key[1],
                        'lineage_reconciled': not hard, 'closed_month': period is not None and period < cutoff,
                        'source_quality_review': source_quality, 'source_records': len(refs), 'reasons': reasons})
        if reasons:
            issues.append(metrics[-1])
        if period is not None:
            series[key[0]].append((period, row, metrics[-1]))
    summaries = []
    for sid, records in sorted(series.items()):
        units = {r['unit'] for _, r, _ in records}
        original_order = [p for p, _, _ in records]
        closed = sorted((p, r, m) for p, r, m in records if m['closed_month'] and m['lineage_reconciled'])
        periods = [p for p, _, _ in closed]
        gaps = sorted(set(range(min(periods), max(periods) + 1)) - set(periods)) if periods else []
        n = len(closed)
        ntrain, nval = int(.7*n), int(.85*n) - int(.7*n)
        # Predeclared technical sufficiency screen, not proof of forecast accuracy.
        eligible = (original_order == sorted(original_order) and
                    ntrain >= 24 and nval >= 6 and n - ntrain - nval >= 6 and
                    not gaps and len(units) == 1 and len(periods) == len(set(periods)))
        summaries.append({'series_id': sid, 'rows': len(records), 'closed_reconciled_rows': n,
                          'units': sorted(units), 'sorted': original_order == sorted(original_order),
                          'missing_months': len(gaps), 'missing_month_numbers': gaps,
                          'technical_split_screen_pass': eligible,
                          'proposed_train': ntrain, 'proposed_validation': nval,
                          'proposed_test': n - ntrain - nval,
                          'source_quality_review_rows': sum(m['source_quality_review'] for _, _, m in closed)})
    return {'audit_version': VERSION, 'as_of': as_of, 'rows': len(rows), 'series_count': len(series),
            'reconciled_rows': sum(m['lineage_reconciled'] for m in metrics),
            'open_or_future_month_rows': sum(not m['closed_month'] for m in metrics),
            'source_quality_review_rows': sum(m['source_quality_review'] for m in metrics),
            'issue_rows': issues, 'series': summaries,
            'limitations': ['Reconciliation validates extraction lineage, not PDF transcription accuracy.',
                            'Closed month does not establish complete weekly publisher coverage.',
                            'Publication dates and historical data vintages are unavailable.',
                            'No observation is an observed total event cost.',
                            'The technical split screen does not establish predictive skill.']}


def audit_project(root, as_of):
    root = Path(root)
    paths = ['data/processed/inflation.csv', 'data/processed/retail_prices.csv',
             'data/final/prophet_cost_timeseries.csv', 'data/raw/extractions/Inflation.csv',
             'data/raw/extractions/Retail_Prices.csv']
    hashes = {p: sha(root / p) for p in paths}
    inflation, retail = [read_csv(root / p) for p in paths[:2]]
    result = reconcile(read_csv(root / paths[2]), inflation, retail, as_of)
    errors, content_errors = [], []
    for name, records in [('Inflation', inflation), ('Retail_Prices', retail)]:
        rawpath = f'data/raw/extractions/{name}.csv'
        raw = read_csv(root / rawpath)
        for record in records:
            try:
                index = int(record['source_csv_row'])
                rid = f"{name}:" + hashlib.sha256((hashes[rawpath] + ':' + str(index)).encode()).hexdigest()[:20]
                if not 2 <= index <= len(raw) + 1 or record['source_extract_sha256'] != hashes[rawpath] or record['source_record_id'] != rid:
                    raise ValueError()
                original = raw[index - 2]
                fields = [('source_id', 'Source_ID', False)]
                if name == 'Inflation':
                    fields += [('index_type', 'Index_Type', False), ('base_year', 'Base_Year', True),
                               ('index_value', 'Index_Value', True), ('month', 'Month', False)]
                else:
                    fields += [('reported_week', 'Reported_Week', False), ('year', 'Year', True),
                               ('month', 'Month', True), ('item_raw', 'Item_Raw', False),
                               ('unit_raw', 'Unit_Raw', False), ('current_price_lkr', 'Current_Price_LKR', True),
                               ('parse_status', 'Parse_Status', False)]
                for processed_key, raw_key, numeric in fields:
                    left, right = record[processed_key].strip(), original[raw_key].strip()
                    if numeric:
                        equal = (not left and not right) or (bool(left) and bool(right) and
                                math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-8))
                    else:
                        equal = left == right
                    if not equal:
                        content_errors.append({'record_id': rid, 'field': processed_key})
            except (KeyError, ValueError):
                errors.append(record.get('source_record_id'))
    result['extraction_identity_errors'] = errors
    result['extraction_content_errors'] = content_errors
    result['source_hashes'] = hashes
    result['code_sha256'] = sha(Path(__file__))
    result['original_inputs_preserved'] = all(sha(root / p) == h for p, h in hashes.items())
    return result
