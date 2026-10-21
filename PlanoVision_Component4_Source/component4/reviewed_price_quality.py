"""Pinned source-value review overlay; frozen measurements and forecast models stay unchanged."""
import hashlib
import json
from pathlib import Path

BASE='data/reviewed/historical_quality_v0_3_20261021/'
MANIFEST_SHA256='88a89ad0153f04cfe9998c57c3ac43d20648f5bc84378d5806128575017c4fe9'

def load_review(root,source_snapshot_sha256):
    root=Path(root);raw=(root/(BASE+'manifest.json')).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('source_review_manifest_hash_mismatch')
    manifest=json.loads(raw)
    if manifest['source_snapshot_sha256']!=source_snapshot_sha256:raise ValueError('source_review_snapshot_mismatch')
    payload={}
    for name,digest in manifest['files'].items():
        if Path(name).name!=name:raise ValueError('unsafe_source_review_artifact')
        value=(root/(BASE+name)).read_bytes()
        if hashlib.sha256(value).hexdigest()!=digest:raise ValueError('source_review_artifact_hash_mismatch')
        payload[name]=json.loads(value)
    review=payload['review.json']
    if review['original_values_changed']!=0 or review['original_flags_removed']!=0:raise ValueError('source_review_requires_new_forecast_fit')
    return review

def quality_for(info,review):
    rows=[r for r in review['observations'] if r['series_id']==info['series_id']]
    if len(rows)!=info['training_records'] or sum(bool(r['quality_flag']) for r in rows)!=info['training_quality_flag_count']:
        raise ValueError('source_review_series_coverage_mismatch')
    ids={r['observation_id'] for r in rows}
    conflicts=sum('conflict_retained' in c['period_resolution'] for c in review['source_decisions'] if c['observation_id'] in ids)
    return {'version':review['version'],'manifest_sha256':MANIFEST_SHA256,
            'source_snapshot_sha256':review['source_hashes']['outputs/experiments/v1.2/future_prices_20261018_v0_1/source_snapshot.csv'],
            'original_flags_preserved':True,'reviewed_records':len(rows),
            'model_value_unresolved_count':sum(r['model_value_review_status']!='retained_publisher_value_confirmed' for r in rows),
            'publisher_period_conflict_count':conflicts,
            'review_method':review['review_method'],'independent_market_validation':False}
