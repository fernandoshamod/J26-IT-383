"""Checksum-pinned historical forecast replay; never extrapolates or alters budgets."""
import csv
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import io
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='outputs/experiments/v1.0/prophet_historical_v0_1_native_20261012/'
FILES={'selected_models.json':'c89eb47d2b3149c500888d697d3fb4b288c4d62612aaeb86f5de95bb7677c303',
       'heldout_forecasts.csv':'d02eb6f4e5d0b5e0df0a194f1d6026ed5d8d35595547f7f858f5762dad9c3fbc'}


def artifacts(root=ROOT):
    data={}
    for name,digest in FILES.items():
        content=(root/(BASE+name)).read_bytes()
        if hashlib.sha256(content).hexdigest()!=digest:raise ValueError('historical_forecast_source_hash_mismatch')
        data[name]=content.decode('utf-8-sig')
    return json.loads(data['selected_models.json']),list(csv.DictReader(io.StringIO(data['heldout_forecasts.csv'])))


def catalog(root=ROOT):
    selected,rows=artifacts(root);series=[]
    for sid,info in selected.items():
        part=[r for r in rows if r['series_id']==sid and r['model']==info['selected_model']]
        series.append({'series_id':sid,'unit':info['unit'],'selected_model':info['selected_model'],
                       'forecast_origin':info['forecast_origin'],'first_replay_month':min(r['ds'] for r in part),
                       'last_replay_month':max(r['ds'] for r in part),'source_id':part[0]['source_id'],
                       'scope':'ingredient_component' if info['unit'].startswith('LKR/') else 'market_context_only',
                       'validation_mae_in_series_unit':info['validation_mae']})
    return {'version':'historical-forecast-bridge.v1','mode':'archived_retrospective_replay_only',
            'series':series,'source_hashes':{BASE+k:v for k,v in FILES.items()},
            'limitations':['No retraining or live prediction. Values are saved validation/test forecasts, not current quotations.',
                           'No complete-event, hotel-package, AV, furniture, labour or venue forecast is defined.',
                           'Index values are not LKR. No automatic event-ledger adjustment or food-to-package uplift is permitted.',
                           'New event dates beyond archived coverage require an explicitly versioned refreshed forecast and evidence review.']}


def preview(payload,root=ROOT):
    required={'series_id','target_month','unit','quantity','expense_scope'}
    if not isinstance(payload,dict) or set(payload)!=required:raise ValueError('exact_forecast_preview_fields_required')
    try:target=date.fromisoformat(payload['target_month'])
    except (TypeError,ValueError):raise ValueError('month_start_date_required') from None
    if target.day!=1 or target.isoformat()!=payload['target_month']:raise ValueError('month_start_date_required')
    selected,rows=artifacts(root);sid=payload['series_id']
    if not isinstance(sid,str) or sid not in selected:raise ValueError('unknown_historical_series')
    info=selected[sid]
    if payload['unit']!=info['unit']:raise ValueError('forecast_unit_mismatch_no_conversion')
    ingredient=info['unit'].startswith('LKR/')
    if payload['expense_scope']!=('ingredient_component' if ingredient else 'market_context_only'):
        raise ValueError('unsupported_forecast_mapping_no_whole_package_indexation')
    quantity=payload['quantity']
    if ingredient:
        if isinstance(quantity,bool) or not isinstance(quantity,(int,float)) or not math.isfinite(quantity) or not 0<quantity<=1e6:
            raise ValueError('positive_quantity_in_series_unit_required')
    elif quantity is not None:raise ValueError('index_is_not_a_currency_amount')
    part=[r for r in rows if r['series_id']==sid and r['model']==info['selected_model']]
    result={'status':'blocked','mode':'archived_retrospective_replay_only','series_id':sid,
            'source_id':part[0]['source_id'],'target_month':payload['target_month'],'unit':info['unit'],
            'model':info['selected_model'],'forecast_origin':info['forecast_origin'],
            'last_supported_month':max(r['ds'] for r in part),'forecast_yhat':None,'ingredient_subtotal_lkr':None,
            'applied_to_event_budget':False,'calibrated_current_event_forecast':False,
            'reason':'target_month_outside_archived_forecast_coverage','source_hashes':{BASE+k:v for k,v in FILES.items()}}
    matching=[r for r in part if r['ds']==payload['target_month']]
    if not matching:return result
    if len(matching)!=1:raise ValueError('ambiguous_archived_forecast')
    row=matching[0];prediction=float(row['forecast_yhat'])
    if not math.isfinite(prediction) or prediction<=0:result['reason']='nonpositive_or_invalid_saved_forecast';return result
    result.update(forecast_yhat=prediction,quality_flag=row['quality_flag'],source_quality_review=row['source_quality_review'],
                  horizon_months=int(row['horizon_months']),observation_id=row['observation_id'])
    if row['source_quality_review']!='0' or row['quality_flag']:
        result['reason']='source_quality_review_required_no_cost_conversion';return result
    result.update(status='available_historical_replay',reason='not_a_current_event_forecast')
    if ingredient:
        result['ingredient_subtotal_lkr']=float((Decimal(str(prediction))*Decimal(str(quantity))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    return result
