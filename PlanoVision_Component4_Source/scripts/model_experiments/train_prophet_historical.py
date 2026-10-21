"""Fixed-origin Prophet/baseline evaluation of genuine immutable historical series."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import csv
import hashlib
import importlib.metadata
import io
import json
import logging
import os
from pathlib import Path
import platform
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
chart_cache = ROOT / 'work/prophet_matplotlib_cache'
chart_cache.mkdir(parents=True, exist_ok=True)
os.environ['MPLCONFIGDIR'] = str(chart_cache)
import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json
from component4.historical_forecasting import audit_series, baseline_predictions, forecast_metrics, month_number
from component4.release_input import verified_release, assert_experiment_output,sha256
from component4.risk_experiment import write_table


def run(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    plan_path=ROOT/'config/experiments/prophet_historical.v0.1.json'
    plan=json.loads(plan_path.read_text())
    archive,release=verified_release()
    original=ROOT/release['original_archive']['project_relative_path']
    before=sha256(archive)
    release_hashes={p.name:sha256(p) for p in archive.parent.iterdir() if p.is_file()}
    if before != plan['release_sha256'] or sha256(original)!=before:
        raise ValueError('release_changed')
    names=('prepared/prophet/prophet_cost_timeseries.csv','prepared/prophet/chronological_split_manifest.csv')
    with zipfile.ZipFile(archive) as package:
        manifest=json.loads(package.read('package_manifest.json'))
        payload={name:package.read(name) for name in names}
        for name,data in payload.items():
            if hashlib.sha256(data).hexdigest()!=manifest['files'][name]:
                raise ValueError('input_checksum:'+name)
    rows=list(csv.DictReader(io.StringIO(payload[names[0]].decode('utf-8-sig'))))
    assignments=list(csv.DictReader(io.StringIO(payload[names[1]].decode('utf-8-sig'))))
    groups,audit=audit_series(rows,assignments)
    if len(groups)!=12 or len(rows)!=563:
        raise ValueError('unexpected_frozen_series_scope')
    output=assert_experiment_output(ROOT/'outputs/experiments/v1.0'/run_id)
    report=assert_experiment_output(ROOT/'reports/experiments/v1.0'/run_id)
    if output.exists() or report.exists():
        raise ValueError('refuse_to_overwrite_existing_experiment')
    output.mkdir(parents=True);report.mkdir(parents=True)
    protocol={'plan':plan,'policy_sha256':sha256(plan_path),'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'archive_sha256':before,'input_member_sha256':{name:manifest['files'][name] for name in names},
        'helper_sha256':sha256(ROOT/'component4/historical_forecasting.py'),'trainer_sha256':sha256(Path(__file__)),
        'runtime':{'python':platform.python_version(),**{name:importlib.metadata.version(name) for name in ('prophet','cmdstanpy','numpy','pandas','matplotlib','holidays','stanio')}},
        'state':'RECORDED_BEFORE_FITTING'}
    (output/'experiment_protocol.json').write_text(json.dumps(protocol,indent=2))
    write_table(report/'series_audit.csv',audit)
    predictions,validation_metrics,test_metrics,sensitivity,selected=[],[],[],[],{}
    logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
    figures=[]
    for index,(sid,data) in enumerate(sorted(groups.items())):
        training=[r for r in data if r['partition']=='train']
        held=[r for r in data if r['partition']!='train']
        train_frame=pd.DataFrame({'ds':pd.to_datetime([r['ds'] for r in training]),'y':[float(r['y']) for r in training]})
        dates=pd.DataFrame({'ds':pd.to_datetime([r['ds'] for r in held])})
        model=Prophet(**plan['prophet_parameters'])
        model.fit(train_frame,seed=plan['random_seed'])
        prophet_forecast=model.predict(dates)['yhat'].to_numpy()
        if not np.isfinite(prophet_forecast).all():
            raise ValueError('nonfinite_prophet_forecast:'+sid)
        model_name='series_'+hashlib.sha256(sid.encode()).hexdigest()[:12]+'.prophet.json'
        serialized=model_to_json(model)
        (output/model_name).write_text(serialized,encoding='utf-8')
        restored=model_from_json(serialized)
        if not np.allclose(restored.predict(dates)['yhat'].to_numpy(),prophet_forecast,rtol=1e-10,atol=1e-10):
            raise ValueError('model_serialization_replay_failed')
        forecasts={'last_value':baseline_predictions(training,[r['ds'] for r in held],'last_value'),
                   'seasonal_naive_12':baseline_predictions(training,[r['ds'] for r in held],'seasonal_naive_12'),
                   'prophet':prophet_forecast.tolist()}
        scores={}
        origin=training[-1]['ds']
        for method,values in forecasts.items():
            for split,destination in (('validation',validation_metrics),('test',test_metrics)):
                positions=[i for i,r in enumerate(held) if r['partition']==split]
                actual=[float(held[i]['y']) for i in positions]
                estimated=[values[i] for i in positions]
                metrics=forecast_metrics(actual,estimated,[r['y'] for r in training])
                destination.append({'series_id':sid,'source_id':data[0]['source_id'],'unit':data[0]['unit'],'model':method,
                    'split':split,'rows':len(positions),'forecast_origin':origin,
                    'first_horizon_months':month_number(held[positions[0]]['ds'])-month_number(origin),
                    'last_horizon_months':month_number(held[positions[-1]]['ds'])-month_number(origin),**metrics})
                if split=='validation':scores[method]=metrics['mae']
                clean=[i for i in positions if held[i]['source_quality_review']!='1']
                sensitivity.append({'series_id':sid,'unit':data[0]['unit'],'model':method,'split':split,
                    'unflagged_evaluation_rows':len(clean),'excluded_flagged_evaluation_rows':len(positions)-len(clean),
                    **(forecast_metrics([held[i]['y'] for i in clean],[values[i] for i in clean],[r['y'] for r in training]) if clean else {k:None for k in metrics})})
            for row,value in zip(held,values):
                predictions.append({'observation_id':row['observation_id'],'series_id':sid,'source_id':row['source_id'],
                    'ds':row['ds'],'split':row['partition'],'unit':row['unit'],'currency':row.get('currency',''),
                    'model':method,'observed_y':float(row['y']),'forecast_yhat':float(value),'forecast_origin':origin,
                    'horizon_months':month_number(row['ds'])-month_number(origin),'source_quality_review':row['source_quality_review'],
                    'quality_flag':row['quality_flag'],'observation_kind':row['observation_kind'],
                    'scope':'retrospective_monthly_price_or_index_not_event_total_cost'})
        chosen=min(scores,key=lambda name:(scores[name],name))
        selected[sid]={'selected_model':chosen,'validation_mae':scores[chosen],'unit':data[0]['unit'],
            'prophet_model_file':model_name,'forecast_origin':origin,'training_records':len(training),
            'baseline_state':{'training_ds':[r['ds'] for r in training],'training_y':[float(r['y']) for r in training]},
            'series_source_quality_flag_count':sum(r['source_quality_review']=='1' for r in data)}
        figures.append((sid,data,held,forecasts,chosen))
        print('Fitted historical series',index+1,'/ 12:',sid,'validation choice:',chosen,flush=True)
    for collection in (validation_metrics,test_metrics,sensitivity):
        for r in collection:r['validation_selected_model']=r['model']==selected[r['series_id']]['selected_model']
    write_table(report/'validation_metrics.csv',validation_metrics)
    write_table(report/'test_metrics.csv',test_metrics)
    write_table(report/'quality_flag_sensitivity.csv',sensitivity)
    write_table(output/'heldout_forecasts.csv',predictions)
    (output/'selected_models.json').write_text(json.dumps(selected,indent=2))
    # Every output is read back. Observation values remain identical to the archive.
    original_values={r['observation_id']:float(r['y']) for r in rows}
    with (output/'heldout_forecasts.csv').open(encoding='utf-8',newline='') as source:
        restored_rows=list(csv.DictReader(source))
    if len(restored_rows)!=525 or len({(r['observation_id'],r['model']) for r in restored_rows})!=525:
        raise ValueError('forecast_export_count_or_duplicate')
    if any(float(r['observed_y'])!=original_values[r['observation_id']] or r['split']=='train' or month_number(r['ds'])<=month_number(r['forecast_origin']) for r in restored_rows):
        raise ValueError('heldout_value_or_chronology_failure')
    for name,count in (('series_audit.csv',12),('validation_metrics.csv',36),('test_metrics.csv',36),('quality_flag_sensitivity.csv',72)):
        with (report/name).open(encoding='utf-8',newline='') as source:
            if sum(1 for _ in csv.DictReader(source))!=count:raise ValueError('report_count:'+name)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,3,figsize=(16,13),layout='constrained')
    for ax,(sid,data,held,forecasts,chosen) in zip(axes.flat,figures):
        ax.plot(pd.to_datetime([r['ds'] for r in data]),[float(r['y']) for r in data],color='#222222',label='Observed',linewidth=1.4)
        ax.plot(pd.to_datetime([r['ds'] for r in held]),forecasts['prophet'],color='#2563eb',label='Prophet',linewidth=1.3)
        ax.plot(pd.to_datetime([r['ds'] for r in held]),forecasts[chosen],color='#e07a21',label='Validation choice',linestyle='--',linewidth=1.3)
        origin=next(r['forecast_origin'] for r in audit if r['series_id']==sid)
        ax.axvline(pd.Timestamp(origin),color='#888888',linestyle=':',linewidth=1)
        ax.axvline(pd.Timestamp(next(r['ds'] for r in held if r['partition']=='test')),color='#b45309',linestyle=':',linewidth=1)
        flagged=[r for r in data if r['source_quality_review']=='1']
        ax.scatter(pd.to_datetime([r['ds'] for r in flagged]),[float(r['y']) for r in flagged],facecolors='none',edgecolors='#b45309',s=20,label='Source review flag')
        ax.set_title(sid.replace('S003:','').replace('S001:','').replace('S002:',''),fontsize=10)
        ax.set_ylabel(data[0]['unit'],fontsize=8);ax.tick_params(axis='both',labelsize=8);ax.grid(alpha=0.15)
    handles,labels=axes.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside upper center',ncol=4,fontsize=10)
    fig.suptitle('Historical monthly forecasts: fixed training origin; separate units; source flags preserved',fontsize=13)
    fig.savefig(assert_experiment_output(report/'historical_forecast_overview.png'),dpi=130);plt.close(fig)
    verified_release()
    if sha256(original)!=before or any(sha256(archive.parent/name)!=digest for name,digest in release_hashes.items()):
        raise ValueError('release_changed_during_forecasting')
    selected_test=[r for r in test_metrics if r['validation_selected_model']]
    prophet_better_than_last=sum(next(r['mae'] for r in test_metrics if r['series_id']==sid and r['model']=='prophet') < next(r['mae'] for r in test_metrics if r['series_id']==sid and r['model']=='last_value') for sid in groups)
    summary={'status':'PASS_EXPLORATORY_RETROSPECTIVE_FORECASTING','historical_records':len(rows),'series_trained':12,
        'prophet_models_saved':12,'partition_records':dict(Counter(r['partition'] for data in groups.values() for r in data)),
        'heldout_observations':175,'forecast_rows_all_methods':525,'selected_model_counts':dict(Counter(r['selected_model'] for r in selected.values())),
        'selected_test_metrics':selected_test,'prophet_test_MAE_better_than_last_value_series':prophet_better_than_last,
        'source_quality_flagged_monthly_records':sum(r['source_quality_review']=='1' for r in rows),
        'nonpositive_forecasts':sum(r['forecast_yhat']<=0 for r in predictions),'forecast_intervals_produced':False,
        'monthly_chronology_checks':'PASS','model_serialization_replay':'PASS','release_before_sha256':before,'release_after_sha256':sha256(archive),
        'release_unchanged':True,'real_event_cost_model':False,'real_time_forecast_validity_established':False,
        'runtime':protocol['runtime'],'model_directory':str(output),'report_directory':str(report)}
    (report/'experiment_summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# Historical forecasting experiment v0.1','','12 separate Prophet models; 563 genuine monthly observations. Targets are ingredient price aggregates or index points, never complete event costs.','',
        '| Series | Unit | Validation choice | Test MAE | Test RMSE | Test seasonal MASE |','|---|---|---|---:|---:|---:|']
    for r in selected_test:
        mase=f"{r['mase_seasonal12']:.3f}" if r['mase_seasonal12'] is not None else 'unavailable'
        lines.append(f"| {r['series_id']} | {r['unit']} | {r['model']} | {r['mae']:.3f} | {r['rmse']:.3f} | {mase} |")
    lines += ['', '## Interpretation and limitations','',
        'The three fixed methods were declared before fitting. Each series fits training only, forecasts validation and test from the same end-of-training origin, and selects by validation MAE. Test compares the predeclared fixed methods once; no test-driven retuning, transformation, refit, outlier removal or clipping. This is a retrospective fixed-origin experiment, not rolling-origin evaluation, real-time validation or a deployed forecast. Test horizons are 8–18 months after each series training cutoff; see exact horizons in metrics.',
        'MAE/RMSE retain each series unit; do not pool LKR commodities, different package sizes and inflation-index values. Seasonal MASE uses lag-12 training differences only; zero denominators remain unavailable. No classification-style accuracy percentage is assigned to regression forecasts. Monthly dates are period keys, not known publication/release timestamps. Different series have different cutoffs and are not joined into a pooled forecaster.',
        '108 monthly records preserve unresolved source quality flags. Flags may indicate review candidates rather than proven transcription errors; all archived values remain intact. The unflagged-evaluation sensitivity does not remove flagged training observations or independently establish source validity. Read these results as exploratory pending source review.',
        '450 food-price targets are aggregates of collected weekly measurements, not new direct monthly transactions. CCPI/NCPI retain their own base-2021 index identity. No LKR series is converted into unitless scenario coefficients. Public data observations do not constitute actual complete event-financial outcomes.',
        'Annual Fourier order 3 is a fixed parsimonious experimental choice, not a calibrated economic assumption. Short histories, Sri Lankan crisis-era changes and long fixed-origin horizons can cause extrapolation failures. Negative forecasts are flagged, not silently corrected. Uncertainty sampling is disabled; there are no validated prediction intervals. Better test scores do not validate an event-budget model.',
        'All 7500 scenarios, release bytes and splits remain unchanged. Financial-risk experiment outputs were not overwritten. GNN/GAT training and frontend changes are not part of this step.',
        '', '## Reproduce (Windows)','', '```powershell','./work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/train_prophet_historical.py --run-id prophet_historical_v0_1_replay','```',
        'Use a new run ID. Exact dependencies and code/input hashes are recorded in the model directory. Prophet models use JSON serialization; selected baseline state is in selected_models.json.',
        '', '## Methods references','', '[Prophet monthly-data guidance](https://facebook.github.io/prophet/docs/non-daily_data.html)', '[Prophet fit/predict API](https://facebook.github.io/prophet/docs/quick_start.html)']
    (report/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Snapshot the complete experiment environment without changing the archived dataset requirements.
    packages=sorted((dist.metadata['Name'],dist.version) for dist in importlib.metadata.distributions() if dist.metadata.get('Name'))
    (output/'requirements.txt').write_text('\n'.join(f'{name}=={version}' for name,version in packages)+'\n')
    (report/'checksums.sha256').write_text(''.join(sha256(p)+'  '+str(p.relative_to(ROOT)).replace('\\','/')+'\n' for p in sorted(list(output.iterdir())+list(report.iterdir())) if p.is_file()))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',default='prophet_historical_v0_1_20261012')
    run(parser.parse_args().run_id)
