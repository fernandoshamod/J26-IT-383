"""Conservative independent-table cleaning; no unsupported international joins."""
import json, re, hashlib
import pandas as pd
import numpy as np
from common import ROOT,RAW,REPORTS,PROCESSED,FINAL,normalize,sha
from features import engineer,POST_EVENT
from inspect_sources import DATA_TABLES

def run():
    PROCESSED.mkdir(parents=True,exist_ok=True);FINAL.mkdir(parents=True,exist_ok=True)
    cleaned={};log=[];lineage=[];mapping=[]
    direct={('Events','Arrive Date'):('Event_Date','MM/DD/YYYY to ISO; planned arrival, not procurement date','date','date'),
            ('Events','Event Name'):('Event_Type','Reviewed keyword classification; retain original name; unmatched remains Unknown','text','category')}
    for name in DATA_TABLES:
        src=RAW/'extractions'/f'{name}.csv'
        d=pd.read_csv(src,low_memory=False);original=d.copy();headers=list(d.columns)
        for c in [c for c in d if pd.api.types.is_string_dtype(d[c])]:
            d[c]=d[c].str.strip().replace({'':pd.NA,'#DIV/0!':pd.NA,'#N/A':pd.NA})
        # Only exact content duplicates, excluding extraction file identity, are removed.
        keys=[c for c in d if c!='Source_File'] if name in {'Inflation','Retail_Prices'} else list(d.columns)
        duplicate=d.duplicated(subset=keys)
        ambiguous_duplicate=d.duplicated(subset=keys,keep=False) if name=='Retail_Prices' else pd.Series(False,index=d.index)
        # Lost PDF group headings can make distinct sub-items look identical.
        # Without a unique publisher record identity those are review candidates, not proven duplicates.
        if name=='Retail_Prices':duplicate=pd.Series(False,index=d.index)
        duplicate_count=int(duplicate.sum())
        source_rows=pd.Series(np.arange(2,len(d)+2),index=d.index)
        d=d.loc[~duplicate].copy();source_rows=source_rows.loc[d.index]
        source_hash=sha(src)
        d['Source_Record_ID']=[f'{name}:{hashlib.sha256((source_hash+":"+str(r)).encode()).hexdigest()[:20]}' for r in source_rows]
        d['Source_CSV_Row']=source_rows
        d['Source_Extract_SHA256']=source_hash
        d['Quality_Flag']=''
        d.loc[ambiguous_duplicate.loc[d.index],'Quality_Flag']+='duplicate_content_requires_pdf_context;'
        for c in [c for c in headers if c in {'Arrive Date','Depart Date','Month','Award_Date'}]:
            if c=='Month' and name!='Inflation':continue
            fmt='%m/%d/%Y' if c in {'Arrive Date','Depart Date'} else 'mixed'
            date=pd.to_datetime(d[c],errors='coerce',format=fmt,utc=True)
            invalid=d[c].notna()&date.isna()
            d.loc[invalid,'Quality_Flag']+=f'invalid_date:{c};'
            d[c]=date.dt.strftime('%Y-%m-%d')
        if name=='Events':
            a=pd.to_datetime(d['Arrive Date']);b=pd.to_datetime(d['Depart Date'])
            d.loc[b<a,'Quality_Flag']+='departure_before_arrival;'
        numeric=[c for c in headers if pd.api.types.is_numeric_dtype(original[c])]
        for c in numeric:
            s=pd.to_numeric(d[c],errors='coerce')
            if re.search(r'Cost|Price|Award_Value|Capacity|Attendance|price|Number_stores|Purchase_grams|Unit_value',c) and not re.search(r'Pct|index|se_',c):
                d.loc[s<0,'Quality_Flag']+=f'negative:{c};'
            q1,q3=s.quantile([.25,.75]);iqr=q3-q1
            if pd.notna(iqr) and iqr>0:d.loc[(s<q1-1.5*iqr)|(s>q3+1.5*iqr),'Quality_Flag']+=f'iqr_review:{c};'
        if name=='Retail_Prices':d.loc[d.Parse_Status!='Parsed','Quality_Flag']+='incomplete_pdf_price_group;'
        if name=='UK_Service_Awards':d['Currency']=d.Currency.str.upper();d['Quality_Flag']+='service_relevance_review;no_fx_conversion;'
        if name=='SL_Procurement':d['Quality_Flag']+='overlapping_aggregate_periods;not_event_quote;'
        if name=='CBSL_Prices_Wages':d['Quality_Flag']+='cell_level;header_interpretation_required;'
        for c in headers:
            sids=sorted(original.Source_ID.dropna().unique())
            for sid in sids:
                target,rule,unit,tunit=direct.get((name,c),('', 'Keep as independent source context. No direct event-financial mapping.',
                    'LKR per Unit_Raw' if name=='Retail_Prices' and 'Price_LKR' in c else
                    'persons' if c in {'Capacity','Attendance'} else 'award currency' if c=='Award_Value' else
                    'LKR million' if c=='Awarded_Value_LKR_Million' else 'publisher-defined (see unit register)','unchanged'))
                include='Conditional' if target else ('Exclude' if c in {'Phone Number','Telephone','Contact'} else 'Context only')
                reason=('Arrival supplies observed event context, not observed costs.' if target=='Event_Date' else
                        'Name supplies only provisional event classification.' if target else
                        'Capacity is not floor area or actual seating.' if c=='Capacity' else
                        'Contract value requires category, duration, quantity and FX calibration; not a per-event quote.' if c=='Award_Value' else
                        'No confirmed semantic match to the 46-field master. Retain provenance and independent table.')
                mapping.append({'Source_ID':sid,'Dataset_Name':name,'Original_Column':c,'Target_Column':target,
                                'Transformation_Rule':rule,'Original_Unit':unit,'Target_Unit':tunit,
                                'Missing_Value_Strategy':'Preserve null. No random fill or global imputation.',
                                'Data_Quality_Status':'Review flagged rows; do not train on them by default.',
                                'Include_or_Exclude':include,'Reason':reason})
        d.columns=[normalize(c) for c in d]
        assert len(set(d.columns))==len(d.columns),'Normalized name collision'
        d.to_csv(PROCESSED/f'{normalize(name)}.csv',index=False)
        cleaned[name]=d
        lineage.extend({'record_id':r.source_record_id,'source_id':r.source_id,'source_file':str(src.relative_to(ROOT)),
                        'source_csv_row':int(r.source_csv_row),'source_sha256':r.source_extract_sha256,'record_kind':'derived_from_public_source',
                        'publisher_locator':'Use source_file/PDF_Page or source_sheet/source_cell columns where present'} for r in d.itertuples())
        log.append({'dataset':name,'before':len(original),'after':len(d),'exact_duplicates_removed':duplicate_count,
                    'flagged_rows':int(d.quality_flag.ne('').sum()),'columns':json.dumps(list(d))})
    pd.DataFrame(log).to_csv(REPORTS/'cleaning_log.csv',index=False)
    pd.DataFrame(lineage).to_csv(REPORTS/'source_provenance.csv',index=False)
    pd.DataFrame(mapping).to_csv(REPORTS/'source_mapping.csv',index=False)
    schema=json.loads((ROOT/'work/original_schema.json').read_text(encoding='utf-8'))
    fields=schema['Master_Data']['data'][0]
    events=cleaned['Events'];master=pd.DataFrame(index=events.index,columns=fields)
    ids=events.source_record_id.str.split(':').str[-1]
    master['Scenario_ID']='OBS-'+ids;master['Base_Event_ID']='EV-'+ids;master['Event_ID']='EV-'+ids
    master['Is_Augmented']=0;master['Data_Source']='S015 observed public event context; financial outcomes unavailable'
    master['Event_Date']=events.arrive_date
    master['Month']=pd.to_datetime(master.Event_Date).dt.month.astype('Int64')
    def category(s):
        for word,label in [('conference','Conference'),('festival','Festival'),('exhibition','Exhibition'),('birthday','Birthday'),('wedding','Wedding')]:
            if word in str(s).lower():return label
        return 'Unknown'
    master['Event_Type']=events.event_name.map(category)
    master=engineer(master)[fields]
    master.to_csv(FINAL/'master_event_context.csv',index=False)
    master.to_csv(FINAL/'master_event_financial_dataset.csv',index=False)
    pd.DataFrame({'Scenario_ID':master.Scenario_ID,'Source_Record_ID':events.source_record_id,
                  'Record_Kind':'observed_event_context_only','Label_Origin':'missing_actual_outcomes',
                  'Financial_Currency':'not available','Classification_Status':'provisional keyword / Unknown'}).to_csv(FINAL/'master_provenance.csv',index=False)
    ts=[]
    inflation=cleaned['Inflation']
    for r in inflation.itertuples():
        if pd.notna(r.index_value):ts.append({'ds':r.month,'y':r.index_value,'cost_category':'inflation_index',
                                             'series_id':f'{r.source_id}:{r.index_type}:base{r.base_year}',
                                             'source_id':r.source_id,'unit':'index (base 2021)','observation_kind':'observed_monthly_index',
                                             'provenance':r.source_record_id,'quality_flag':r.quality_flag})
    retail=cleaned['Retail_Prices'];good=retail[retail.parse_status.eq('Parsed')&retail.current_price_lkr.gt(0)&retail.unit_raw.notna()]
    # Abbreviated PDF sub-items cannot be unambiguously named; keep them out of forecasting.
    good=good[~good.item_raw.str.match(r'^(Imported|Local|No[ .]|Red$|White$)',case=False,na=False)]
    for keys,g in good.groupby(['year','month','item_raw','unit_raw']):
        year,month,item,unit=keys
        if g.reported_week.duplicated().any():continue
        ts.append({'ds':f'{int(year):04d}-{int(month):02d}-01','y':g.current_price_lkr.mean(),
                   'cost_category':'ingredient_price_proxy','series_id':f'S003:{item}:{unit}',
                   'source_id':'S003','unit':f'LKR/{unit}','observation_kind':'monthly mean of published weekly prices',
                   'provenance':';'.join(g.source_record_id),'reported_weeks':g.reported_week.nunique(),
                   'quality_flag':'review_source_outliers;' if g.quality_flag.ne('').any() else ''})
    times=pd.DataFrame(ts).sort_values(['series_id','ds']);times.to_csv(FINAL/'prophet_cost_timeseries.csv',index=False)
    eligible=[f for f in fields if f not in POST_EVENT and f not in {'Scenario_ID','Base_Event_ID','Event_ID','Is_Augmented','Data_Source'}]
    pd.DataFrame({'Field':fields,'Role':['target_or_post_event_exclude' if f in POST_EVENT else
                  'identifier_exclude' if f not in eligible else 'planning_candidate_requires_timestamp' for f in fields]}).to_csv(REPORTS/'feature_eligibility.csv',index=False)
    # Explicit empty, schema-correct training dataset. Unlabelled contexts must not masquerade as labelled examples.
    pd.DataFrame(columns=['Scenario_ID','Base_Event_ID',*eligible,'Budget_Overrun','Profit_Margin_Risk','Vendor_Cost_Anomaly']).to_csv(FINAL/'xgboost_risk_dataset.csv',index=False)
    graph=FINAL/'spatial_financial_graphs';graph.mkdir(exist_ok=True)
    (graph/'STATUS.json').write_text(json.dumps({'status':'not_generated','reason':'No observed geometry or calibrated event financial dependencies. Simulator assumptions need explicit review.'},indent=2))
    print('PREPROCESS_COMPLETE',len(master),'event contexts;',len(times),'time-series rows; 0 labelled risk examples',flush=True)
if __name__=='__main__':run()
