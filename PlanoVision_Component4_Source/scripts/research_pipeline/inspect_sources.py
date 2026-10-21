"""Inspect originals and extraction tables without mutating their values."""
import sys, json, gzip, shutil, warnings, hashlib
from collections import Counter
from pathlib import Path
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from pypdf import PdfReader
from common import ROOT,COLLECTION,RAW,REPORTS,profile,sha

DATA_TABLES=['Inflation','Retail_Prices','Venues','Events','USDA_Away','USDA_Home_National',
             'USDA_Home_Supplement','UK_Service_Awards','SL_Procurement','CBSL_Prices_Wages']
def run():
    REPORTS.mkdir(exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
    found=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.suffix.lower() in {'.csv','.xlsx','.xls','.json','.parquet','.gz','.pdf'}:
            if any(part in {'data','reports','.git','__pycache__'} for part in p.relative_to(ROOT).parts):continue
            found.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,
                          'role':'temporary Excel lock (excluded)' if p.name.startswith('~$') else
                          'publisher original' if 'raw_datasets' in p.parts else 'schema or generated artifact (not independent evidence)'})
    pd.DataFrame(found).to_csv(REPORTS/'discovered_files.csv',index=False)
    manifest=json.loads((COLLECTION/'download_manifest.json').read_text())
    for m in manifest:
        src=COLLECTION/m['file'];dst=RAW/'publishers'/m['source_id']/m['name']
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():shutil.copy2(src,dst)
        assert sha(dst)==m['sha256'],str(dst)
    schema=RAW/'schema'/'DataSet_original.xlsx';schema.parent.mkdir(exist_ok=True)
    if not schema.exists():shutil.copy2(COLLECTION/'raw_inputs'/'DataSet_original.xlsx',schema)
    (RAW/'extractions').mkdir(exist_ok=True)
    inventory=[];profiles=[]
    for name in DATA_TABLES:
        src=COLLECTION/'processed_csv'/f'{name}.csv';dst=RAW/'extractions'/src.name
        if not dst.exists():shutil.copy2(src,dst)
        assert sha(src)==sha(dst)
        df=pd.read_csv(dst,low_memory=False)
        sid=';'.join(sorted(df['Source_ID'].dropna().unique()))
        grain={'CBSL_Prices_Wages':'Original spreadsheet cell, NOT an observation',
               'SL_Procurement':'Entity x overlapping period x competitiveness aggregate',
               'Retail_Prices':'Reported week x publisher item label x unit',
               'UK_Service_Awards':'Selected award within contracting process'}.get(name,'Source-specific observation; never independent event-financial outcome')
        inv,cols=profile(df,dst,name,grain,sid,'Extracted table; original source remains authoritative')
        inventory.append(inv);profiles.extend(cols)
        print('PROFILE',name,len(df),flush=True)
    for p in sorted((RAW/'publishers').rglob('*')):
        if not p.is_file():continue
        sid=p.parent.name
        if p.suffix=='.pdf':
            inventory.append({'file':str(p.relative_to(ROOT)),'source_id':sid,'table':'PDF',
                              'records':None,'columns':'[]','row_grain':'PDF pages, not observations',
                              'pages':len(PdfReader(p).pages),'sha256':sha(p),
                              'quality':'See extracted tables and extraction exceptions; PDFs require publisher-layout interpretation',
                              'profile_status':'Page count and integrity; tabular profiles in extraction entries'})
        elif p.suffix=='.csv':
            df=pd.read_csv(p,low_memory=False)
            inv,cols=profile(df,p,'CSV','Publisher CSV observation',sid,'Publisher original')
            inventory.append(inv);profiles.extend(cols)
        elif p.suffix=='.xlsx':
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
            for sheet in wb:
                rows=[list(r) for r in sheet.iter_rows(values_only=True) if any(v is not None for v in r)]
                if not rows:continue
                width=max(map(len,rows));rows=[r+[None]*(width-len(r)) for r in rows]
                # Only explicitly structured USDA Data sheets have verified row-1 headers.
                structured=sid in {'S010','S018'} and sheet.title.lower()=='data'
                if structured:
                    header_row=1 if sid=='S010' else 0
                    headers=[str(x) if x is not None else f'unnamed_{i}' for i,x in enumerate(rows[header_row])]
                    df=pd.DataFrame(rows[header_row+1:],columns=headers)
                else:
                    df=pd.DataFrame(rows,columns=[f'Source_Column_{get_column_letter(i+1)}' for i in range(width)])
                inv,cols=profile(df,p,sheet.title,'Publisher data row' if structured else 'Nonempty physical spreadsheet row, NOT confirmed records',sid,
                                 'Structured publisher Data sheet' if structured else 'Header/layout interpretation required; do not auto-map physical columns')
                inventory.append(inv);profiles.extend(cols)
                print('XLSX',p.name,sheet.title,len(df),flush=True)
            wb.close()
        elif p.name.endswith('.jsonl.gz'):
            count=0;keys=Counter();awards=0;dates=[];currencies=Counter();award_rows=[];digests=set();duplicates=0
            with gzip.open(p,'rt',encoding='utf-8') as f:
                for line in f:
                    obj=json.loads(line);count+=1;keys.update(obj.keys())
                    digest=hashlib.sha256(line.strip().encode()).digest()
                    duplicates+=int(digest in digests);digests.add(digest)
                    release=obj.get('compiledRelease',obj)
                    if release.get('date'):dates.append(release['date'])
                    for a in release.get('awards',[]):
                        awards+=1
                        if a.get('value',{}).get('currency'):currencies.update([a['value']['currency']])
                        award_rows.append({'OCID':release.get('ocid',obj.get('ocid')),'Award_ID':a.get('id'),
                                           'Award_Date':a.get('date'),'Award_Value':a.get('value',{}).get('amount'),
                                           'Currency':a.get('value',{}).get('currency'),'Status':a.get('status')})
            inventory.append({'file':str(p.relative_to(ROOT)),'source_id':sid,'table':'JSONL processes','records':count,
                              'columns':json.dumps(sorted(keys)),'dtypes':'Nested JSON; not a flat event table','duplicate_content_rows':duplicates,
                              'row_grain':'Contracting process; awards nested','sha256':sha(p),'nested_awards':awards,
                              'date_min':min(dates) if dates else None,'date_max':max(dates) if dates else None,
                              'currencies':json.dumps(currencies),'quality':'Full process scan; broad selected service awards need relevance review',
                              'profile_status':'Top-level key missingness and nested award metadata; quantitative award profiles in extracted selection'})
            for k,n in keys.items():profiles.append({'file':str(p.relative_to(ROOT)),'table':'JSONL processes','source_id':sid,
                                                     'column':k,'dtype':'nested JSON','missing_pct':100*(1-n/count),'nonmissing':n})
            all_awards=pd.DataFrame(award_rows)
            for currency,g in all_awards.groupby('Currency',dropna=False):
                inv,cols=profile(g,p,'Nested awards '+str(currency),'Nested award; overlaps selected award extraction',sid,'All nested awards; no relevance filtering or currency conversion')
                inventory.append(inv);profiles.extend(cols)
            print('JSONL',p.name,count,flush=True)
    w=openpyxl.load_workbook(schema,read_only=True,data_only=True)
    for s in w:
        vals=list(s.values);df=pd.DataFrame(vals[1:],columns=vals[0]);inv,cols=profile(df,schema,s.title,'Original schema/dictionary, NOT event evidence','schema','User original')
        inventory.append(inv);profiles.extend(cols)
    w.close()
    pd.DataFrame(inventory).to_csv(REPORTS/'dataset_inventory.csv',index=False)
    pd.DataFrame(profiles).to_csv(REPORTS/'column_profiles.csv',index=False)
    (REPORTS/'inventory_summary.json').write_text(json.dumps({'discovered_files':len(found),'publisher_files':len(manifest),
                                                            'inventory_tables':len(inventory),'profiled_columns':len(profiles)},indent=2))
    print('INSPECTION_COMPLETE',len(inventory),len(profiles),flush=True)
if __name__=='__main__':run()
