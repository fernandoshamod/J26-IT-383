"""Build a clearly labelled simulation bundle from the user's verified vendor CSV.
Run locally. No network access or additional packages beyond pandas/numpy required.
"""
from pathlib import Path
from itertools import combinations
import argparse
import json
import hashlib
import numpy as np
import pandas as pd

VERSION = 'simulation-v1'
# Illustrative USD ranges, NOT researched market prices or vendor quotations.
ASSUMPTIONS = {
    'Catering': ('per_person', 15, 65),
    'Photography': ('fixed_package', 400, 2200),
    'Decoration': ('fixed_package', 300, 2500),
    'Entertainment': ('per_hour', 80, 350),
    'Audio Visual': ('fixed_package', 250, 1800),
    'Equipment Rental': ('fixed_package', 150, 1400),
    'Event Planning': ('fixed_package', 400, 2500),
}

def build(source, output, seed=42):
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise FileNotFoundError(f'Upload/copy the verified vendor CSV to: {source}')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory is not empty. Use a new directory to preserve earlier runs.')
    real = pd.read_csv(source, encoding='utf-8-sig', dtype={'business_id': 'string'})
    required = ['business_id', 'name', 'city', 'state', 'service_categories', 'risk_level', 'vendor_score']
    missing = set(required) - set(real.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    ids = real.business_id.fillna('').str.strip()
    if ids.eq('').any() or ids.str.startswith('#').any() or ids.duplicated().any():
        raise ValueError('Missing, corrupted or duplicate business IDs. Repair before generation.')
    real['business_id'] = ids
    pairs = []
    for row in real.itertuples(index=False):
        for service in sorted(set(str(row.service_categories).split(';'))):
            service = service.strip()
            if service not in ASSUMPTIONS:
                raise ValueError(f'Unknown service category: {service}')
            pairs.append((row.business_id, service, row.city, row.state))
    if not pairs:
        raise ValueError('No vendor-service pairs.')
    rng = np.random.default_rng(seed)
    output.mkdir(parents=True, exist_ok=True)
    counts = {}
    def save(name, rows):
        frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        frame.to_csv(output / name, index=False, encoding='utf-8-sig')
        counts[name] = len(frame)
        return frame

    # Preserve the real input exactly at the table level. Its derived labels/scores
    # remain derived, not independently verified real-world risk ground truth.
    save('real_vendor_profiles.csv', real)
    options = []
    for i, (bid, service, city, state) in enumerate(pairs):
        basis, lo, hi = ASSUMPTIONS[service]
        for tier, multiplier in [('Basic', 1.0), ('Standard', 1.4), ('Premium', 1.9)]:
            cap = int(rng.choice([50, 100, 150, 200, 300, 500])) if service == 'Catering' else None
            options.append({
                'service_option_id': f'SIMOPT-{i:06d}-{tier[0]}',
                'business_id': bid, 'service_category': service, 'option_tier': tier,
                'supported_event_types': 'Wedding; Corporate; Birthday',
                'unit_price': round(float(rng.uniform(lo, hi) * multiplier), 2),
                'currency': 'USD', 'pricing_basis': basis,
                'min_billable_guests': 20 if basis == 'per_person' else None,
                'max_guests': cap,
                'guest_capacity_applicability': 'simulated_catering_limit' if cap else 'not_modelled',
                'min_billable_hours': 2 if basis == 'per_hour' else None,
                'simulated_service_city': city, 'simulated_service_state': state,
                'setup_space_m2': int(rng.integers(5, 61)),
                'power_kw': round(float(rng.uniform(0.2, 8)), 2),
                'setup_minutes': int(rng.choice([30, 60, 90, 120])),
                'backup_capability': str(rng.choice(['simulated_yes', 'simulated_no'])),
                'service_features': f'SIMULATED {tier} {service} option; no verified inclusions',
                'data_origin': 'synthetic', 'is_vendor_confirmed': False,
                'assumption_source': 'illustrative developer assumptions; not market research',
                'generation_version': VERSION,
            })
    opt = save('synthetic_service_options.csv', options)
    assert opt.service_option_id.is_unique
    assert opt.business_id.isin(real.business_id).all()
    assert opt.unit_price.gt(0).all()

    # Pilot locations for simulation, not real bookings. Date windows are explicit
    # simulation settings. Venue validation deliberately stays unmodelled.
    usable = real.dropna(subset=['city', 'state']).copy()
    if usable.empty:
        raise ValueError('No populated city/state values for event scenarios.')
    locations = usable[['city', 'state']].drop_duplicates().sort_values(['state', 'city'])
    chosen = locations.iloc[rng.choice(len(locations), min(10, len(locations)), replace=False)]
    events, availability, candidate_ids = [], [], {}
    for n in range(30):
        loc = chosen.iloc[n % len(chosen)]
        local = usable[(usable.city == loc.city) & (usable.state == loc.state)]
        available_services = sorted({s.strip() for v in local.service_categories for s in v.split(';')})
        selected_services = sorted(rng.choice(available_services, min(3, len(available_services)), replace=False))
        eid = f'SIMEVT-{n:04d}'
        date = (pd.Timestamp('2027-01-01') + pd.Timedelta(days=n * 3)).strftime('%Y-%m-%d')
        events.append({
            'event_id': eid, 'event_type': str(rng.choice(['Wedding', 'Corporate', 'Birthday'])),
            'event_date': date, 'start_time': '14:00', 'end_time': '18:00', 'duration_hours': 4,
            'city': loc.city, 'state': loc.state, 'guest_count': int(rng.choice([50, 100, 200, 350])),
            'budget': int(rng.integers(1000, 20001)), 'currency': 'USD',
            'required_services': '; '.join(selected_services),
            'venue_status': 'Not evaluated', 'data_origin': 'synthetic', 'generation_version': VERSION,
        })
        # Limit the pilot to up to ten candidates per service, not every local business.
        pool = set()
        for service in selected_services:
            mask = local.service_categories.apply(lambda x: service in {s.strip() for s in x.split(';')})
            pool.update(local.loc[mask].sort_values('vendor_score', ascending=False).head(10).business_id)
        candidate_ids[eid] = sorted(pool)
        for bid in sorted(pool):
            availability.append({
                'event_id': eid, 'business_id': bid, 'event_date': date,
                'availability_status': str(rng.choice(['available', 'unavailable', 'unknown'], p=[0.65, 0.25, 0.10])),
                'checked_interval_start': '14:00', 'checked_interval_end': '18:00',
                'data_origin': 'synthetic', 'is_vendor_confirmed': False, 'generation_version': VERSION,
            })
    ev = save('synthetic_event_requirements.csv', events)
    av = save('synthetic_availability.csv', availability)
    assert not av.duplicated(['event_id', 'business_id']).any()
    assert av.business_id.isin(real.business_id).all()

    # Simulated collaboration outcomes, never real vendor history. These labels
    # are not an independently validated ML target. Entire pairs share a split.
    histories = []
    for event in events:
        pool = candidate_ids[event['event_id']]
        for a, b in list(combinations(pool, 2))[:20]:
            pair_id = hashlib.sha256((a + '|' + b).encode()).hexdigest()[:16]
            bucket = int(pair_id[:8], 16) % 10
            split = 'train' if bucket < 7 else ('validation' if bucket < 9 else 'test')
            histories.append({
                'simulated_collaboration_id': f'SIMCOL-{len(histories):06d}',
                'event_id': event['event_id'], 'pair_id': pair_id,
                'vendor_a_id': a, 'vendor_b_id': b,
                'simulated_conflict': int(rng.random() < 0.25),
                'outcome_origin': 'synthetic_random_simulator_not_ground_truth',
                'data_origin': 'synthetic', 'is_actual_collaboration': False,
                'pair_group_split': split, 'generation_version': VERSION,
            })
    hist = save('synthetic_collaboration_scenarios.csv', histories)
    if not hist.empty:
        assert hist.groupby('pair_id').pair_group_split.nunique().max() == 1

    # Flattened view for convenience; real and synthetic fields remain distinguishable.
    flat = opt.merge(real.add_prefix('profile_'), left_on='business_id', right_on='profile_business_id', validate='many_to_one')
    flat['record_origin'] = 'hybrid_real_profile_plus_synthetic_service_option'
    save('hybrid_vendor_service_dataset.csv', flat)
    provenance = []
    for col in real.columns:
        origin = 'derived_rule_or_score' if col in ['risk_level','risk_score','rating_score','review_score','stability_score','vendor_score','vendor_rank'] else 'user_supplied_profile_or_review_feature'
        provenance.append({'table': 'real_vendor_profiles.csv', 'field': col, 'origin': origin})
    for col in opt.columns:
        provenance.append({'table': 'synthetic_service_options.csv', 'field': col, 'origin': 'real_foreign_key' if col == 'business_id' else 'synthetic_or_simulation_metadata'})
    save('field_provenance.csv', provenance)
    manifest = {
        'version': VERSION, 'seed': seed, 'source': str(source),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'rows': counts, 'price_assumptions': ASSUMPTIONS,
        'limitations': [
            'Not a verified complete real-world dataset.',
            'USD is a simulation currency, not a confirmed vendor quotation currency.',
            'Synthetic prices, capacities, service areas, backup and availability are NOT vendor facts.',
            'Synthetic collaboration rows are NOT evidence these vendors worked together.',
            'Risk labels and vendor scores in the real input are derived, not operational-risk ground truth.',
            'No venue, safety, tax, travel-fee or actual scheduling validation.',
            'Random synthetic outcomes are only pipeline tests; not meaningful real-world ML evaluation.',
            'No actual vendor-specific free-text inclusions are supplied.',
        ],
    }
    (output / 'dataset_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('COMPLETED: labelled prototype dataset bundle')
    for filename, count in counts.items():
        print(filename, ':', count)
    print('Saved to:', output)
    return counts

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=r'D:\Vendor-Intelligence-System\vendor_recommendation_dataset_ids_checked.csv')
    parser.add_argument('--output', default=r'D:\Vendor-Intelligence-System\hybrid_simulation_v1')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    build(args.source, args.output, args.seed)
