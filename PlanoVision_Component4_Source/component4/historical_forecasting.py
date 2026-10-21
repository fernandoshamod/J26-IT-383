"""Leakage-safe monthly forecasting helpers, independent of Prophet installation."""
from collections import defaultdict
from datetime import date
import math


def month_number(value):
    d = date.fromisoformat(value)
    if d.day != 1:
        raise ValueError('month_start_required')
    return d.year * 12 + d.month - 1


def audit_series(rows, assignments):
    by_id = {r['observation_id']: r for r in assignments}
    if len(by_id) != len(assignments) or set(by_id) != {r['observation_id'] for r in rows}:
        raise ValueError('duplicate_or_missing_partition_assignment')
    groups = defaultdict(list)
    if len({r['observation_id'] for r in rows}) != len(rows):
        raise ValueError('duplicate_observation_id')
    for r in rows:
        if r['synthetic_origin'] != '0' or r['event_total_cost_observation'] != '0':
            raise ValueError('not_genuine_separate_series')
        if r['lineage_reconciled'] != '1' or r['closed_calendar_month'] != '1':
            raise ValueError('unreconciled_or_open_month')
        if not math.isfinite(float(r['y'])) or float(r['y']) <= 0:
            raise ValueError('invalid_observed_measurement')
        groups[r['series_id']].append(dict(r, partition=by_id[r['observation_id']]['partition']))
    reports = []
    for sid, data in sorted(groups.items()):
        data.sort(key=lambda r:r['ds'])
        months = [month_number(r['ds']) for r in data]
        if months != list(range(months[0],months[-1]+1)):
            raise ValueError('duplicate_or_missing_month')
        if len({(r['source_id'],r['unit'],r.get('currency','')) for r in data}) != 1:
            raise ValueError('mixed_measurement_units_or_sources')
        ranks = {'train':0,'validation':1,'test':2}
        if any(r['partition'] not in ranks for r in data):
            raise ValueError('invalid_partition')
        order = [ranks[r['partition']] for r in data]
        if order != sorted(order):
            raise ValueError('nonchronological_partition')
        subsets = {s:[r for r in data if r['partition']==s] for s in ranks}
        if len(subsets['train']) < 24 or len(subsets['validation']) < 6 or len(subsets['test']) < 6:
            raise ValueError('insufficient_history')
        reports.append({'series_id':sid,'source_id':data[0]['source_id'],'unit':data[0]['unit'],
            'currency':data[0].get('currency',''),'total_records':len(data),
            'train_records':len(subsets['train']),'validation_records':len(subsets['validation']),'test_records':len(subsets['test']),
            'train_start':subsets['train'][0]['ds'],'forecast_origin':subsets['train'][-1]['ds'],
            'validation_start':subsets['validation'][0]['ds'],'validation_end':subsets['validation'][-1]['ds'],
            'test_start':subsets['test'][0]['ds'],'test_end':subsets['test'][-1]['ds'],
            'quality_flagged_records':sum(r['source_quality_review']=='1' for r in data),
            'publication_timestamps_verified':False,'status':'eligible_exploratory_retrospective_forecasting'})
    return dict(groups),reports


def baseline_predictions(training, dates, method):
    ordered = sorted(training,key=lambda r:r['ds'])
    if not ordered:
        raise ValueError('empty_training')
    origin = month_number(ordered[-1]['ds'])
    lookup = {month_number(r['ds']):float(r['y']) for r in ordered}
    predictions = []
    for ds in dates:
        key = month_number(ds)
        if key <= origin:
            raise ValueError('forecast_not_after_training')
        if method == 'last_value':
            predictions.append(float(ordered[-1]['y']))
        elif method == 'seasonal_naive_12':
            while key > origin:
                key -= 12
            if key not in lookup:
                raise ValueError('missing_training_season')
            predictions.append(lookup[key])
        else:
            raise ValueError('unknown_baseline')
    return predictions


def forecast_metrics(actual, predicted, training):
    if len(actual) != len(predicted) or not actual:
        raise ValueError('empty_or_misaligned_predictions')
    actual,predicted,training = list(map(float,actual)),list(map(float,predicted)),list(map(float,training))
    if not all(math.isfinite(v) for v in actual+predicted+training):
        raise ValueError('nonfinite_metric_input')
    absolute = [abs(a-p) for a,p in zip(actual,predicted)]
    mae = math.fsum(absolute)/len(actual)
    scale = math.fsum(abs(training[i]-training[i-12]) for i in range(12,len(training)))/(len(training)-12) if len(training)>12 else 0
    return {'mae':mae, 'rmse':math.sqrt(math.fsum((a-p)**2 for a,p in zip(actual,predicted))/len(actual)),
            'mase_seasonal12':mae/scale if scale>0 else None,
            'training_seasonal_scale':scale if scale>0 else None,
            'smape_percent':math.fsum(200*abs(a-p)/(abs(a)+abs(p)) if abs(a)+abs(p)>0 else 0 for a,p in zip(actual,predicted))/len(actual),
            'nonpositive_prediction_count':sum(p<=0 for p in predicted)}


def expanding_validation_windows(data, horizon=3, folds=3, minimum_training=24):
    """Predeclared expanding windows, stopping before any original test record."""
    if any(type(v) is not int or v <= 0 for v in (horizon, folds, minimum_training)):
        raise ValueError('invalid_window_parameters')
    ordered = sorted(data, key=lambda r: r['ds'])
    if not ordered:
        raise ValueError('empty_window_history')
    dates = [month_number(r['ds']) for r in ordered]
    if dates != list(range(dates[0], dates[-1] + 1)):
        raise ValueError('noncontiguous_window_history')
    training_count = sum(r['partition'] == 'train' for r in ordered)
    cutoffs = [training_count - horizon * i for i in reversed(range(folds))]
    windows = []
    for cutoff in cutoffs:
        training, evaluation = ordered[:cutoff], ordered[cutoff:cutoff + horizon]
        if cutoff < minimum_training or len(evaluation) != horizon:
            raise ValueError('insufficient_window_history')
        if any(r['partition'] != 'train' for r in training) or any(r['partition'] not in ('train', 'validation') for r in evaluation):
            raise ValueError('test_or_validation_record_in_window_training')
        if training[-1]['ds'] >= evaluation[0]['ds']:
            raise ValueError('future_leakage_in_window')
        windows.append((training, evaluation))
    return windows
