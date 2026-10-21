"""Versioned full-history deployment refit. Does not modify frozen data/evaluations."""
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
cache=ROOT/'work/future_price_matplotlib_cache'
cache.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(cache)
from component4.release_input import verified_release,sha256
from component4.forecast_bridge import artifacts,BASE,FILES

OUT=ROOT/'outputs/experiments/v1.2/future_prices_20261018_v0_1'


def next_month(value,offset):
    year,month=map(int,value[:7].split('-'));n=year*12+month-1+offset
    return f'{n//12:04d}-{n%12+1:02d}-01'


def run():
    import numpy as np
    import pandas as pd
    from prophet import Prophet
    from prophet.serialize import model_to_json,model_from_json
    if OUT.exists():raise ValueError('refuse_existing_deployment')
    archive,release=verified_release();before=sha256(archive)
    selected,_=artifacts()
    policy_path=ROOT/'config/experiments/future_price_deployment.v0.1.json'
    policy=json.loads(policy_path.read_text())
    member='prepared/prophet/prophet_cost_timeseries.csv'
    with zipfile.ZipFile(archive) as z:
        raw=z.read(member);manifest=json.loads(z.read('package_manifest.json'))
        if hashlib.sha256(raw).hexdigest()!=manifest['files'][member]:raise ValueError('source_hash_mismatch')
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(rows)!=563:raise ValueError('unexpected_scope')
    OUT.mkdir(parents=True)
    (OUT/'source_snapshot.csv').write_bytes(raw)
    all_series=[];forecast_rows=[]
    for sid,selection in sorted(selected.items()):
        part=sorted((r for r in rows if r['series_id']==sid),key=lambda r:r['ds'])
        ds=[r['ds'] for r in part];ys=[float(r['y']) for r in part]
        if len(set(ds))!=len(ds) or len(part)<36 or not np.isfinite(ys).all() or min(ys)<=0:
            raise ValueError('invalid_series:'+sid)
        if ds!=[next_month(ds[0],i) for i in range(len(ds))]:raise ValueError('noncontiguous_series')
        if any(r['synthetic_origin']!='0' or r['unit']!=selection['unit'] for r in part):raise ValueError('invalid_lineage')
        origin=ds[-1];dates=[next_month(origin,i) for i in range(1,policy['horizon_months']+1)]
        frame=pd.DataFrame({'ds':pd.to_datetime(dates)})
        method=selection['selected_model'];model_file=None
        if method=='prophet':
            model=Prophet(**policy['prophet_parameters'])
            model.fit(pd.DataFrame({'ds':pd.to_datetime(ds),'y':ys}),seed=policy['seed'])
            values=model.predict(frame)['yhat'].to_numpy()
            model_file='series_'+hashlib.sha256(sid.encode()).hexdigest()[:12]+'.prophet.json'
            encoded=model_to_json(model);(OUT/model_file).write_text(encoded,encoding='utf-8')
            if not np.allclose(values,model_from_json(encoded).predict(frame)['yhat'].to_numpy(),rtol=1e-10,atol=1e-10):raise ValueError('replay_failed')
        elif method=='last_value':values=np.repeat(ys[-1],len(dates))
        else:raise ValueError('unsupported_selected_method')
        if not np.isfinite(values).all():raise ValueError('nonfinite_prediction')
        flagged=sum(r['source_quality_review']!='0' or bool(r['quality_flag']) for r in part)
        info={'series_id':sid,'unit':selection['unit'],'source_id':part[0]['source_id'],'method':method,
              'training_records':len(part),'first_observation':ds[0],'forecast_origin':origin,
              'last_observed_y':ys[-1],'first_forecast_month':dates[0],'last_forecast_month':dates[-1],
              'training_quality_flag_count':flagged,'publication_timestamps_verified':False,
              'scope':'ingredient_component' if selection['unit'].startswith('LKR/') else 'market_context_only',
              'model_file':model_file,'previous_validation_mae':selection['validation_mae'],
              'previous_mae_is_not_new_deployment_accuracy':True}
        all_series.append(info)
        forecast_rows.extend({'series_id':sid,'ds':d,'yhat':float(v),'horizon_months':i+1} for i,(d,v) in enumerate(zip(dates,values)))
        print(sid,method,len(part),'quality flags',flagged,flush=True)
    (OUT/'forecasts.json').write_text(json.dumps({'series':all_series,'forecasts':forecast_rows},indent=2,allow_nan=False),encoding='utf-8')
    files={p.name:sha256(p) for p in OUT.iterdir() if p.is_file()}
    record={'version':policy['version'],'status':'EXPLORATORY_DEPLOYMENT_NOT_MARKET_VALIDATED',
            'created_at_utc':datetime.now(timezone.utc).isoformat(),'policy':policy,'policy_sha256':sha256(policy_path),
            'release_sha256':before,'source_member':member,'source_member_sha256':hashlib.sha256(raw).hexdigest(),
            'old_evaluation_hashes':{BASE+k:v for k,v in FILES.items()},'files':files,
            'runtime':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ('prophet','numpy','pandas','cmdstanpy')}},
            'code_sha256':sha256(Path(__file__)),'records':len(rows),'series':len(all_series),'forecast_records':len(forecast_rows),
            'new_independent_accuracy_estimate':None,'calibrated_current_event_forecast':False,
            'limitations':['Full-history refit, not a new independent test.','Unresolved quality flags preserved; flagged series cannot supply monetary ingredient estimates.',
                            'Publication timing and full publisher coverage not independently established.','No complete-event or vendor service-price forecast. No automatic budget application.']}
    if sha256(archive)!=before:raise ValueError('immutable_release_changed')
    artifacts() # Original selected models and heldout forecasts still checksum-identical.
    (OUT/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('MANIFEST SHA256',sha256(OUT/'manifest.json'),flush=True)


if __name__=='__main__':run()
