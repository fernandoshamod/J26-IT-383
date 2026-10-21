"""Render saved historical forecasts only; do not refit models or alter tables."""
import csv
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(ROOT/'work/prophet_matplotlib_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from component4.release_input import verified_release,assert_experiment_output,sha256


def render(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    output=assert_experiment_output(ROOT/'outputs/experiments/v1.0'/run_id)
    report=assert_experiment_output(ROOT/'reports/experiments/v1.0'/run_id)
    selected=json.loads((output/'selected_models.json').read_text())
    with (output/'heldout_forecasts.csv').open(encoding='utf-8',newline='') as source:
        forecasts=list(csv.DictReader(source))
    table_model_hashes={str(p):sha256(p) for p in list(output.iterdir())+list(report.glob('*.csv')) if p.is_file()}
    archive,_=verified_release()
    with zipfile.ZipFile(archive) as package:
        observations=list(csv.DictReader(io.StringIO(package.read('prepared/prophet/prophet_cost_timeseries.csv').decode('utf-8-sig'))))
    fig,axes=plt.subplots(4,3,figsize=(16,13))
    fig.subplots_adjust(top=0.91,bottom=0.045,left=0.07,right=0.99,hspace=0.37,wspace=0.27)
    for ax,(sid,metadata) in zip(axes.flat,sorted(selected.items())):
        data=sorted((r for r in observations if r['series_id']==sid),key=lambda r:r['ds'])
        held=sorted((r for r in forecasts if r['series_id']==sid and r['model']=='prophet'),key=lambda r:r['ds'])
        winner=sorted((r for r in forecasts if r['series_id']==sid and r['model']==metadata['selected_model']),key=lambda r:r['ds'])
        ax.plot(pd.to_datetime([r['ds'] for r in data]),[float(r['y']) for r in data],color='#222222',label='Observed',linewidth=1.4)
        ax.plot(pd.to_datetime([r['ds'] for r in held]),[float(r['forecast_yhat']) for r in held],color='#2563eb',label='Prophet',linewidth=1.3)
        ax.plot(pd.to_datetime([r['ds'] for r in winner]),[float(r['forecast_yhat']) for r in winner],color='#e07a21',label='Validation choice',linestyle='--',linewidth=1.3)
        ax.axvline(pd.Timestamp(metadata['forecast_origin']),color='#888888',linestyle=':',linewidth=1)
        ax.axvline(pd.Timestamp(next(r['ds'] for r in held if r['split']=='test')),color='#b45309',linestyle=':',linewidth=1)
        flagged=[r for r in data if r['source_quality_review']=='1']
        ax.scatter(pd.to_datetime([r['ds'] for r in flagged]),[float(r['y']) for r in flagged],facecolors='none',edgecolors='#b45309',s=20,label='Source review flag')
        ax.set_title(sid.split(':',1)[1],fontsize=10)
        ax.set_ylabel(data[0]['unit'],fontsize=8)
        ax.tick_params(axis='both',labelsize=7)
        ax.grid(alpha=0.15)
    handles,labels=axes.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(0.5,0.962),ncol=4,fontsize=10)
    fig.suptitle('Historical monthly forecasts: fixed training origin; separate units; source flags preserved',fontsize=13,y=0.985)
    png=report/'historical_forecast_overview.png'
    fig.savefig(png,dpi=130);plt.close(fig)
    if any(sha256(path)!=digest for path,digest in table_model_hashes.items()):
        raise ValueError('chart_rerender_changed_model_or_table')
    verified_release()
    receipt={'operation':'figure_layout_only_no_refitting_or_metric_changes','rendered_at_utc':datetime.now(timezone.utc).isoformat(),
        'script_sha256':sha256(Path(__file__)),'png_sha256':sha256(png),'model_and_table_checksums_unchanged':True,
        'reproduce_command':f'./work/component4_ml_venv/Scripts/python.exe scripts/model_experiments/render_prophet_overview.py {run_id}'}
    (report/'figure_render_receipt.json').write_text(json.dumps(receipt,indent=2))
    checksum=report/'checksums.sha256'
    checksum.write_text(''.join(sha256(p)+'  '+str(p.relative_to(ROOT)).replace('\\','/')+'\n' for p in sorted(list(output.iterdir())+list(report.iterdir())) if p.is_file() and p!=checksum))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    render(sys.argv[1])
