"""Shared paths and deterministic, conservative source profiling."""
from pathlib import Path
import hashlib, json, re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
COLLECTION=ROOT/'outputs'/'01a12103-7a09-7331-bb93-9e24a6f05005'
RAW=ROOT/'data'/'raw'
REPORTS=ROOT/'reports'
PROCESSED=ROOT/'data'/'processed'
FINAL=ROOT/'data'/'final'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def normalize(name):
    return re.sub(r'[^a-z0-9]+','_',str(name).strip().lower()).strip('_')

def profile(df,path,table,grain,source_id,quality):
    columns=[]
    for name in df:
        s=df[name]; numeric=pd.to_numeric(s,errors='coerce')
        count=int(s.notna().sum()); numeric_count=int(numeric.notna().sum())
        quantitative=numeric_count>0 and numeric_count==count
        stats={}
        if quantitative:
            finite=numeric[np.isfinite(numeric)]
            if len(finite):
                q1,q3=finite.quantile([.25,.75]);iqr=q3-q1
                stats={'min':float(finite.min()),'q25':float(q1),'median':float(finite.median()),
                       'q75':float(q3),'max':float(finite.max()),'mean':float(finite.mean()),
                       'std':float(finite.std()) if len(finite)>1 else None,
                       'negative_count':int((finite<0).sum()),
                       'iqr_outlier_count':int(((finite<q1-1.5*iqr)|(finite>q3+1.5*iqr)).sum()) if iqr>0 else None}
        date_min=date_max=None
        if re.search(r'date|^ds$|^month$',str(name),re.I) and not quantitative:
            dates=pd.to_datetime(s,errors='coerce',format='mixed',utc=True)
            if dates.notna().any():date_min=str(dates.min());date_max=str(dates.max())
        columns.append({'file':str(path.relative_to(ROOT)), 'table':table,'source_id':source_id,
                        'column':str(name),'dtype':str(s.dtype),'missing_pct':round(100*(1-count/len(s)),4) if len(s) else None,
                        'nonmissing':count,'numeric_count':numeric_count,'date_min':date_min,'date_max':date_max,**stats})
    inv={'file':str(path.relative_to(ROOT)),'source_id':source_id,'table':table,'records':len(df),
         'columns':json.dumps([str(c) for c in df.columns]),'dtypes':json.dumps({str(c):str(df[c].dtype) for c in df}),
         'duplicate_content_rows':int(df.duplicated().sum()),'row_grain':grain,'quality':quality,
         'sha256':sha(path),'profile_status':'Complete table scan'}
    inv['file_name']=path.name
    inv['missing_percentages']=json.dumps({c['column']:c['missing_pct'] for c in columns})
    inv['date_min']=min([c['date_min'] for c in columns if c['date_min']],default=None)
    inv['date_max']=max([c['date_max'] for c in columns if c['date_max']],default=None)
    inv['currencies']=';'.join(sorted(df['Currency'].dropna().astype(str).unique())) if 'Currency' in df else 'Not monetary / see unit context'
    inv['unit_context']={'Inflation':'index (base 2021); percentage-point changes',
                         'Retail_Prices':'LKR per Unit_Raw; percentages in points',
                         'Venues':'advertised capacity in persons; facilities Y/N; no m2',
                         'Events':'dates; attendance counts missing; no financial units',
                         'USDA_Away':'USD per product; standard error same units',
                         'USDA_Home_National':'USD per 100g unit values; weighted/unweighted USD/grams; GEKS index',
                         'USDA_Home_Supplement':'weighted/unweighted USD/grams and publisher price indexes',
                         'SL_Procurement':'LKR million; counts; overlapping periods',
                         'UK_Service_Awards':'award totals in Currency; not unit service prices',
                         'CBSL_Prices_Wages':'table-specific units require original header interpretation'}.get(table,'Publisher sheet/column-specific; do not infer units from values')
    inv['numerical_distributions']='reports/column_profiles.csv, matched by file + table + column'
    return inv,columns
