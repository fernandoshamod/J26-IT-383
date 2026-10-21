"""Read-only versioned future-price deployment, separate from archived evaluation."""
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
from .reviewed_price_quality import load_review,quality_for

ROOT=Path(__file__).resolve().parents[1]
BASE='outputs/experiments/v1.2/future_prices_20261018_v0_1/'
MANIFEST_SHA256='bf025d9a9e2c6723f2ccc36cc864a826f7471fb6f67eef3e260ccd7373821c50'


def artifacts(root=ROOT):
    raw=(root/(BASE+'manifest.json')).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('future_deployment_manifest_hash_mismatch')
    manifest=json.loads(raw)
    payload={}
    for name,digest in manifest['files'].items():
        if Path(name).name!=name:raise ValueError('invalid_artifact_name')
        data=(root/(BASE+name)).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('future_deployment_artifact_hash_mismatch')
        payload[name]=data
    return manifest,json.loads(payload['forecasts.json'])


def catalog(root=ROOT):
    manifest,data=artifacts(root)
    review=load_review(root,manifest['source_member_sha256'])
    series=[{**s,'quality_review':quality_for(s,review)} for s in data['series']]
    return {'version':manifest['version'],'mode':'exploratory_full_history_deployment',
            'series':series,'manifest_sha256':MANIFEST_SHA256,
            'source_sha256':manifest['source_member_sha256'],'limitations':[v for v in manifest['limitations'] if not v.startswith('Unresolved quality flags')]+[
                'Original source flags remain; a separate pinned field-specific review matches model values to retained publisher columns. This is not independent market validation.',
                'The January 2024 week-4 publisher title says 2023; explicit 2024 current-price/comparison headers determine the period and the conflict remains recorded.'],
            'new_independent_accuracy_estimate':None,'applied_to_event_budget':False}


def preview(payload,root=ROOT):
    if not isinstance(payload,dict) or set(payload)!={'series_id','target_month','unit','quantity','expense_scope'}:
        raise ValueError('exact_future_forecast_fields_required')
    try:target=date.fromisoformat(payload['target_month'])
    except (TypeError,ValueError):raise ValueError('month_start_date_required') from None
    if target.day!=1 or target.isoformat()!=payload['target_month']:raise ValueError('month_start_date_required')
    manifest,data=artifacts(root)
    info=next((s for s in data['series'] if s['series_id']==payload['series_id']),None)
    if info is None:raise ValueError('unknown_future_series')
    if payload['unit']!=info['unit']:raise ValueError('forecast_unit_mismatch_no_conversion')
    if payload['expense_scope']!=info['scope']:raise ValueError('no_whole_package_forecast_mapping')
    quality=quality_for(info,load_review(root,manifest['source_member_sha256']))
    q=payload['quantity']
    if info['scope']=='ingredient_component':
        if isinstance(q,bool) or not isinstance(q,(int,float)) or not math.isfinite(q) or not 0<q<=1e6:
            raise ValueError('positive_quantity_in_published_unit_required')
    elif q is not None:raise ValueError('index_is_not_currency')
    result={'version':manifest['version'],'status':'blocked','mode':'exploratory_full_history_deployment',
            'series_id':info['series_id'],'source_id':info['source_id'],'unit':info['unit'],'model':info['method'],
            'target_month':target.isoformat(),'forecast_origin':info['forecast_origin'],
            'last_supported_month':info['last_forecast_month'],'training_records':info['training_records'],
            'training_quality_flag_count':info['training_quality_flag_count'],
            'quality_review':quality,
            'forecast_yhat':None,'last_observed_y':info['last_observed_y'],'ingredient_subtotal_lkr':None,
            'ingredient_change_from_last_observation_lkr':None,'reason':'outside_frozen_future_horizon',
            'applied_to_event_budget':False,'calibrated_current_event_forecast':False,
            'publication_timestamps_verified':False,'new_independent_accuracy_estimate':None,
            'manifest_sha256':MANIFEST_SHA256}
    row=next((r for r in data['forecasts'] if r['series_id']==info['series_id'] and r['ds']==target.isoformat()),None)
    if row is None:return result
    y=row['yhat']
    if not math.isfinite(y) or y<=0:result['reason']='nonpositive_forecast_no_clipping';return result
    result.update(forecast_yhat=y,horizon_months=row['horizon_months'])
    if quality['model_value_unresolved_count']:
        result.update(status='review_required',reason='training_source_quality_review_required_no_monetary_conversion')
        return result
    result.update(status='available_experimental_forecast',reason='retained_publisher_model_values_reviewed_original_flags_preserved_not_market_validated')
    if info['scope']=='ingredient_component':
        def money(n):return float(n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
        result['ingredient_subtotal_lkr']=money(Decimal(str(y))*Decimal(str(q)))
        result['ingredient_change_from_last_observation_lkr']=money((Decimal(str(y))-Decimal(str(info['last_observed_y'])))*Decimal(str(q)))
    return result
