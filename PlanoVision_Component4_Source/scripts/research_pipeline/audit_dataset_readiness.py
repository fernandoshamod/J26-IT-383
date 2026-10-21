"""Read-only quality audit; never generates scenarios or fits models."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'data/hybrid/Component4_Hybrid_Dataset_Final_v1.0'
OUT = ROOT / 'reports/dataset_quality_audit_20261012'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rows(relative):
    with (PACKAGE / relative).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def run():
    manifest = json.loads((ROOT / 'dataset_releases/v1.0/RELEASE_MANIFEST.json').read_text())
    archives = [ROOT / manifest[k]['project_relative_path'] for k in ('original_archive', 'release_archive')]
    inputs = archives + sorted(p for p in (PACKAGE / 'prepared').rglob('*') if p.is_file())
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    archive_checks = {k: sha(ROOT / manifest[k]['project_relative_path']) == manifest[k]['sha256']
                      for k in ('original_archive', 'release_archive')}
    spec = json.loads((PACKAGE / 'prepared/xgboost/feature_specification.json').read_text())
    financial = rows('prepared/xgboost/xgboost_risk_dataset.csv')
    features = spec['predictors']
    signatures, families, groups = defaultdict(list), defaultdict(set), defaultdict(set)
    for r in financial:
        key = tuple(float(r[f]) for f in features)
        assert all(math.isfinite(v) for v in key)
        signatures[key].append(r)
        families[r['Base_Event_ID']].add(r['split'])
        groups[r['split_group_id']].add(r['split'])
        assert all(r[t] in ('0', '1') for t in spec['targets'])
    overlap = [rs for rs in signatures.values() if len({r['split'] for r in rs}) > 1]
    split_files_match = {}
    for part in ('train', 'validation', 'test'):
        split_files_match[part] = sorted(rows(f'prepared/xgboost/{part}.csv'), key=lambda r: r['Scenario_ID']) == sorted(
            (r for r in financial if r['split'] == part), key=lambda r: r['Scenario_ID'])
    monthly = rows('prepared/prophet/prophet_cost_timeseries.csv')
    partitions = rows('prepared/prophet/chronological_split_manifest.csv')
    partition_by_id = {r['observation_id']: r for r in partitions}
    series = defaultdict(list)
    queue = []
    for r in monthly:
        assert math.isfinite(float(r['y']))
        assert r['observation_id'] in partition_by_id
        series[r['series_id']].append(r)
        if r['quality_flag'].strip():
            queue.append({'table': 'prophet', 'observation_id': r['observation_id'],
                          'series_id': r['series_id'], 'date': r['ds'], 'value': r['y'],
                          'unit': r['unit'], 'source_id': r['source_id'], 'quality_flag': r['quality_flag'],
                          'partition': partition_by_id[r['observation_id']]['partition'],
                          'decision': 'PENDING_SOURCE_REVIEW_NOT_CONFIRMED_ERROR'})
    chronology = {}
    for sid, rs in series.items():
        dates = [r['ds'] for r in rs]
        ordered_parts = [partition_by_id[r['observation_id']]['partition'] for r in sorted(rs, key=lambda r: r['ds'])]
        rank = {'train': 0, 'validation': 1, 'test': 2}
        chronology[sid] = {'rows': len(rs), 'unique_dates': len(set(dates)),
                           'ordered': dates == sorted(dates),
                           'chronological_split': [rank[p] for p in ordered_parts] == sorted(rank[p] for p in ordered_parts),
                           'units': sorted({r['unit'] for r in rs}),
                           'review_rows': sum(bool(r['quality_flag'].strip()) for r in rs)}
    real = []
    for name in ('weekly_retail_observations', 'monthly_inflation_observations'):
        table = rows(f'prepared/real/{name}.csv')
        real.extend(table)
        for r in table:
            if r['quality_flag'].strip():
                queue.append({'table': name, **{k: r.get(k) for k in ('source_record_id', 'source_id', 'source_csv_row',
                               'source_file', 'pdf_page', 'month', 'reported_week', 'unit', 'publisher_url', 'quality_flag')},
                              'decision': 'PENDING_SOURCE_REVIEW_NOT_CONFIRMED_ERROR'})
    graphs = rows('prepared/spatial_financial_graphs/graph_index.csv')
    by_id = {r['Scenario_ID']: r for r in financial}
    graph_alignment = len(graphs) == len(financial) and len({r['graph_id'] for r in graphs}) == len(graphs)
    for g in graphs:
        f = by_id.get(g['graph_id'])
        graph_alignment &= f is not None and all(g[k] == f[k] for k in ('Base_Event_ID', 'split_group_id', 'split', 'configuration_sha256'))
    hotel_path = ROOT / 'outputs/01a12103-7a09-7331-bb93-9e24a6f05005/hotel_evidence_20261012/evidence_metadata.json'
    hotel = json.loads(hotel_path.read_text())
    result = {
        'audit_time_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Read-only existing datasets; no scenario generation, model fitting or source re-download.',
        'archive_checks': archive_checks,
        'synthetic_rows': len(financial), 'root_families': len(families),
        'split_rows': dict(Counter(r['split'] for r in financial)),
        'split_group_counts': dict(Counter(next(iter(s)) for s in groups.values())),
        'cross_split_families': sum(len(s) > 1 for s in families.values()),
        'cross_split_groups': sum(len(s) > 1 for s in groups.values()),
        'unique_scenario_ids': len(by_id), 'split_files_match': split_files_match,
        'forbidden_predictors_present': sorted(set(features) & set(spec['forbidden_inputs'])),
        'cross_split_feature_vectors': len(overlap),
        'cross_split_feature_rows': sum(len(rs) for rs in overlap),
        'overlap_scenario_groups': [[r['Scenario_ID'] for r in rs] for rs in overlap],
        'genuine_historical_measurements': len(real),
        'observed_event_outcomes': sum(r['observed_event_financial_outcome'] == '1' for r in real),
        'historical_flagged_rows': sum(bool(r['quality_flag'].strip()) for r in real),
        'prophet_rows': len(monthly), 'prophet_series': len(series),
        'prophet_flagged_rows': sum(bool(r['quality_flag'].strip()) for r in monthly),
        'prophet_missing_publication_dates': sum(not r['publication_date'].strip() for r in monthly),
        'prophet_duplicate_series_dates': len(monthly) - len({(r['series_id'], r['ds']) for r in monthly}),
        'prophet_open_month_rows': sum(date.fromisoformat(r['ds'][:10]).replace(day=1) >= date(2026, 10, 1) for r in monthly),
        'prophet_series_checks': chronology, 'graph_count': len(graphs),
        'graph_split_and_identity_alignment': bool(graph_alignment),
        'hotel_rate_rows': len(hotel['rates']),
        'hotel_evidence_role': 'Supplementary advertised LKR rate evidence, not observed event outcomes; never merged into dimensionless targets.',
        'review_queue_note': 'Direct source and monthly aggregation flags may overlap in lineage. Counts are not independent errors.',
        'input_checksums_before': before,
    }
    after = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    result['all_audited_inputs_unchanged'] = before == after
    result['status'] = 'REVIEW_REQUIRED_BEFORE_NEW_MODEL_EXPERIMENTS'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (OUT / 'source_quality_review_queue.json').write_text(json.dumps(queue, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_checksums_before', 'prophet_series_checks', 'overlap_scenario_groups')}, indent=2))
    assert all(archive_checks.values()) and result['all_audited_inputs_unchanged']


if __name__ == '__main__':
    run()
