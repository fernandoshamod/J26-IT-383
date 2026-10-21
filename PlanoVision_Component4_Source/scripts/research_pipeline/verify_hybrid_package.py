"""Portable, read-only verification of hybrid model tables and preserved snapshots."""
import csv
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from component4.hybrid_dataset import (FEATURES, FORBIDDEN, TARGETS, NODE_FEATURES,
    NODE_TYPES, EDGE_RULES, chronological_audit, preserved_split_audit, read_csv, sha)


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'package_manifest.json').read_text())
    checks = {}
    def check(name, value):
        checks[name] = bool(value)
        if not value:
            raise ValueError(name)
    check('all_package_file_checksums', all(sha(root / path) == value for path, value in manifest['files'].items()))
    receipt = json.loads((root / 'reports/validation_results.json').read_text())
    check('all_preparation_checks_passed', all(receipt['checks'].values()))
    check('original_synthetic_hashes_preserved', all(sha(root / p) == h for p, h in receipt['synthetic_original_sha256'].items()))
    base = root / 'data/final/unitless-bulk-v0.1'
    master = read_csv(base / 'master_event_financial_dataset.csv')
    provenance = read_csv(base / 'master_scenario_provenance.csv')
    check('original_master_count_schema', len(master) == 7500 and len(master[0]) == 46 and len({r['Scenario_ID'] for r in master}) == 7500)
    check('grouped_leakage_audit', preserved_split_audit(provenance)['status'] == 'PASS')
    by_master = {r['Scenario_ID']: r for r in master}
    by_provenance = {r['scenario_id']: r for r in provenance}
    features = read_csv(root / 'prepared/xgboost/xgboost_risk_dataset.csv')
    spec = json.loads((root / 'prepared/xgboost/feature_specification.json').read_text())
    check('allowlist_matches_no_outcome_features', spec['predictors'] == list(FEATURES) and not set(spec['predictors']).intersection(FORBIDDEN | set(TARGETS)))
    check('xgboost_record_scope', len(features) == 7500 and {r['Scenario_ID'] for r in features} == set(by_master))
    for row in features:
        original, source = by_master[row['Scenario_ID']], by_provenance[row['Scenario_ID']]
        check('xgboost_original_assignment', row['split'] == source['split'] and row['split_group_id'] == source['split_group_id'] and row['Base_Event_ID'] == source['family_id'])
        for key in FEATURES:
            expected = int(original['Event_Type'] == key.removeprefix('Event_Type_')) if key.startswith('Event_Type_') else float(original[key])
            check('xgboost_planning_values_unchanged', float(row[key]) == expected)
        check('targets_match_synthetic_outcomes', all(int(row[k]) == int(original[k] == 'True') for k in TARGETS))
    for split in ('train', 'validation', 'test'):
        check('xgboost_split_' + split, read_csv(root / f'prepared/xgboost/{split}.csv') == [r for r in features if r['split'] == split])
    history = read_csv(root / 'prepared/prophet/prophet_cost_timeseries.csv')
    partitions = read_csv(root / 'prepared/prophet/chronological_split_manifest.csv')
    coverage = chronological_audit(history, partitions)
    check('chronology_separate_series', len(history) == 563 and len(coverage) == 12)
    links = read_csv(root / 'prepared/real/observation_provenance.csv')
    raw = read_csv(root / 'prepared/real/weekly_retail_observations.csv') + read_csv(root / 'prepared/real/monthly_inflation_observations.csv')
    check('1900_genuine_source_record_ids', len(raw) == 1900 and len({r['source_record_id'] for r in raw}) == 1900)
    check('direct_measurement_source_scope', {r['source_record_id'] for r in raw} == {r['source_record_id'] for r in links})
    by_observation = defaultdict(list)
    raw_by_id = {r['source_record_id']: r for r in raw}
    for row in links:
        by_observation[row['observation_id']].append(float(row['source_observed_value']))
        source = raw_by_id[row['source_record_id']]
        value = source['current_price_lkr'] if source['source_id'] == 'S003' else source['index_value']
        check('direct_observed_value_preserved', float(value) == float(row['source_observed_value']) and source['publisher_sha256'] == row['publisher_sha256'])
    for row in history:
        values = by_observation[row['observation_id']]
        check('historical_aggregation_reconciliation', len(values) == int(row['source_record_count']) and math.isclose(float(row['y']), math.fsum(values) / len(values), rel_tol=1e-12))
        check('historical_not_synthetic_or_event_total', row['synthetic_origin'] == '0' and row['event_total_cost_observation'] == '0')
    directory = root / 'prepared/spatial_financial_graphs'
    graphs = read_csv(directory / 'graph_index.csv')
    nodes = read_csv(directory / 'node_features.csv')
    edges = read_csv(directory / 'edges.csv')
    labels = read_csv(directory / 'graph_targets.csv')
    check('graph_counts', len(graphs) == 7500 and len(nodes) == 67500 and len(edges) == 97500 and len(labels) == 7500)
    by_graph = {r['graph_id']: r for r in graphs}
    check('graph_identity_scope', set(by_graph) == set(by_master))
    for graph in graphs:
        source = by_provenance[graph['graph_id']]
        check('graph_split_matches_master', graph['split'] == source['split'] and graph['split_group_id'] == source['split_group_id'])
    expected_nodes = np.full((7500, 9, len(NODE_FEATURES)), np.nan)
    positions = {r['graph_id']: i for i, r in enumerate(graphs)}
    seen_nodes = set()
    for row in nodes:
        node_index = int(row['node_index'])
        key = (row['graph_id'], node_index)
        check('node_reference_unique', key not in seen_nodes and row['graph_id'] in positions and 0 <= node_index < 9 and row['node_type'] == NODE_TYPES[node_index])
        seen_nodes.add(key)
        for column, name in enumerate(NODE_FEATURES):
            if row[name] != '':
                expected_nodes[positions[row['graph_id']], node_index, column] = float(row[name])
    seen_edges = set()
    for row in edges:
        key = row['graph_id'], int(row['edge_id'])
        check('edge_reference_unique', key not in seen_edges and row['graph_id'] in positions)
        seen_edges.add(key)
        rule = EDGE_RULES[int(row['edge_id'])]
        check('edge_semantics', int(row['source_node_index']) == rule[0] and int(row['target_node_index']) == rule[1] and row['relation_type'] == rule[2] and row['edge_origin'] == 'assumed_dependency')
    check('node_fields_exclude_targets', not set(NODE_FEATURES).intersection(FORBIDDEN | set(TARGETS)))
    charges = expected_nodes[:, :, NODE_FEATURES.index('planned_charge_score')]
    for index, graph in enumerate(graphs):
        check('graph_cost_reconciliation', math.isclose(float(np.nansum(charges[index])), float(by_master[graph['graph_id']]['Forecasted_Total_Cost']), rel_tol=1e-12, abs_tol=1e-12))
    with np.load(directory / 'graphs.npz', allow_pickle=False) as data:
        check('npz_all_node_values_and_masks', np.array_equal(data['x'], expected_nodes, equal_nan=True) and np.array_equal(data['feature_mask'], np.isfinite(expected_nodes)))
        check('npz_target_labels', np.array_equal(data['y'], np.array([[int(r[k]) for k in TARGETS] for r in labels])))
        check('npz_graph_split_identity', data['graph_id'].tolist() == [r['graph_id'] for r in graphs] and data['split'].tolist() == [r['split'] for r in graphs])
    for row in labels:
        check('graph_labels_match_master', all(int(row[k]) == int(by_master[row['graph_id']][k] == 'True') for k in TARGETS))
    return {'status': 'PASS', 'checks': checks, 'statistics': manifest['statistics'], 'model_training_performed': False}


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1] if len(sys.argv) > 1 else '.'), indent=2))
