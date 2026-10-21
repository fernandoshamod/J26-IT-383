"""Check partial dataset validity without claiming supervised research readiness."""
import json
import pandas as pd
import numpy as np
from common import ROOT,REPORTS,PROCESSED,FINAL
from features import POST_EVENT

def run():
    schema=json.loads((ROOT/'work/original_schema.json').read_text(encoding='utf-8'))
    fields=schema['Master_Data']['data'][0]
    master=pd.read_csv(FINAL/'master_event_financial_dataset.csv');ts=pd.read_csv(FINAL/'prophet_cost_timeseries.csv')
    provenance=pd.read_csv(FINAL/'master_provenance.csv');risk=pd.read_csv(FINAL/'xgboost_risk_dataset.csv')
    checks={
      '46_original_columns_preserved':list(master)==fields and len(fields)==46,
      'unique_scenario_ids':master.Scenario_ID.is_unique,
      'valid_event_dates':pd.to_datetime(master.Event_Date,errors='coerce').notna().all(),
      'no_fabricated_actuals':master[['Actual_Total_Cost','Actual_Revenue']].isna().all().all(),
      'no_fabricated_labels':master[['Budget_Overrun','Profit_Margin_Risk','Vendor_Cost_Anomaly']].isna().all().all(),
      'no_augmentation':master.Is_Augmented.eq(0).all(),
      'master_lineage_complete':set(master.Scenario_ID)==set(provenance.Scenario_ID),
      'timeseries_unique_keys':not ts.duplicated(['series_id','ds']).any(),
      'timeseries_dates_valid':pd.to_datetime(ts.ds,errors='coerce').notna().all(),
      'timeseries_values_finite_nonnegative':pd.to_numeric(ts.y,errors='coerce').ge(0).all() and np.isfinite(pd.to_numeric(ts.y,errors='coerce')).all(),
      'timeseries_sorted':all(g.ds.is_monotonic_increasing for _,g in ts.groupby('series_id')),
      'no_synthetic_timeseries':~ts.observation_kind.str.contains('synthetic',case=False).any(),
      'empty_risk_training_set_until_labels_available':risk.empty,
      'no_post_event_inputs':not ((POST_EVENT-{'Budget_Overrun','Profit_Margin_Risk','Vendor_Cost_Anomaly'})&set(risk)),
      'no_graph_training_claim':json.loads((FINAL/'spatial_financial_graphs/STATUS.json').read_text())['status']=='not_generated'
    }
    pd.DataFrame([{'field':c,'rows':len(master),'missing_pct':100*master[c].isna().mean(),'unique_nonmissing':master[c].nunique()} for c in master]).to_csv(REPORTS/'final_dataset_statistics.csv',index=False)
    dates=ts.groupby('series_id').agg(rows=('y','size'),first=('ds','min'),last=('ds','max'))
    dates.to_csv(REPORTS/'timeseries_coverage.csv')
    # Partition indices are created from observed chronology only. No model fit, imputation or augmentation.
    partitions=[]
    for sid,g in ts.groupby('series_id'):
        n=len(g)
        if n<24:continue
        for i,r in enumerate(g.itertuples()):
            part='train' if i<int(.7*n) else 'validation' if i<int(.85*n) else 'test'
            partitions.append({'series_id':sid,'ds':r.ds,'partition':part})
    pd.DataFrame(partitions).to_csv(FINAL/'prophet_chronological_partitions.csv',index=False)
    partition_frame=pd.DataFrame(partitions)
    chronological=True
    for _,g in partition_frame.groupby('series_id'):
        groups={part:group.ds for part,group in g.groupby('partition')}
        chronological &= groups['train'].max()<groups['validation'].min() and groups['validation'].max()<groups['test'].min()
    checks['chronological_partitions_disjoint']=chronological and not partition_frame.duplicated(['series_id','ds']).any()
    val='# Partial dataset validation\n\n'
    val+='Automated structural checks: '+('PASS' if all(checks.values()) else 'FAIL')+'. This is NOT supervised event-financial research readiness.\n\n'
    val+='\n'.join(f'- {k}: {"PASS" if v else "FAIL"}' for k,v in checks.items())
    val+='\n\n73 observed event contexts have no calibrated costs, geometry, actual revenue or financial labels. Capacity, arithmetic, target distribution and train/test independence for augmented financial scenarios are NOT TESTABLE yet. Graph structural validation is NOT APPLICABLE (no graphs).\n'
    (REPORTS/'final_dataset_validation.md').write_text(val,encoding='utf-8')
    (REPORTS/'validation_results.json').write_text(json.dumps({k:bool(v) for k,v in checks.items()},indent=2))
    assert all(checks.values()),checks
    dictionary=pd.DataFrame(schema['Data_Dictionary']['data'][1:],columns=schema['Data_Dictionary']['data'][0])
    dictionary['Prediction_Role']=dictionary.Column_Name.map(lambda c:'Exclude: target/post-event' if c in POST_EVENT else 'Identifier' if c in {'Scenario_ID','Base_Event_ID','Event_ID','Is_Augmented','Data_Source'} else 'Planning candidate; require pre-event timestamp')
    dictionary['Current_Missing_Pct']=dictionary.Column_Name.map(master.isna().mean()*100)
    dictionary['Unit_Clarification']=dictionary.Column_Name.map(lambda c:'percentage points (20 = 20%)' if c in {'Profit_Margin','Required_Min_Profit_Margin'} else 'ratio, not percentage points' if c in {'Budget_Utilization','Space_Utilization'} else 'Preserve original definition; unavailable costs must not imply zero')
    dictionary.to_csv(REPORTS/'updated_data_dictionary.csv',index=False)
    log=pd.read_csv(REPORTS/'cleaning_log.csv');inv=pd.read_csv(REPORTS/'dataset_inventory.csv')
    profile=pd.read_csv(REPORTS/'column_profiles.csv')
    quality='# Dataset quality and suitability\n\n'
    quality+='Inventory includes publisher files, each XLSX table, nested JSON process metadata, and separately labelled extracted tables. Do not add their record counts together: CSV/XLSX mirrors and successive CBSL releases overlap. PDF page counts are not record counts.\n\n'
    for r in log.itertuples():quality+=f'- {r.dataset}: {r.before:,} extracted rows, {r.after:,} after {r.exact_duplicates_removed} exact-content duplicates removed, {r.flagged_rows:,} review flags.\n'
    quality+='\n## Measured missingness\n\n'
    for name,col in [('Events','Attendance'),('UK_Service_Awards','Award_Value'),('Retail_Prices','Current_Price_LKR')]:
        row=profile[(profile.table==name)&(profile.column==col)].iloc[0]
        quality+=f'- {name}.{col}: {row.missing_pct:.2f}% missing before cleaning.\n'
    quality+='\n## Supported uses and exclusions\n\n'
    quality+='Sri Lankan inflation and retail observations support separate local forecasting experiments, not actual total event-cost prediction. USDA observations support historical US benchmarking only. UK contract awards require manual scope, quantity and term review. Sri Lankan procurement values are overlapping high-value aggregates and are excluded from event quotations. California capacity/facility flags do not establish m2, Sri Lankan venue prices or spatial adjacency. Austin event names and date ranges do not establish duration hours, realised attendance, costs or revenues. CBSL cell-level extracts require per-table header/unit interpretation before training.\n\n'
    quality+='IQR flags are descriptive screening, not proven anomalies or vendor-anomaly targets. Flagged rows are retained. Retail duplicate-content candidates are NOT removed because their publisher-group context can be ambiguous. Raw currency values are not converted. No exchange rate was invented. No personal contact attributes are prediction inputs. Original PDFs include unsupported rows documented in the earlier Extraction_Log.\n'
    (REPORTS/'dataset_quality_report.md').write_text(quality,encoding='utf-8')
    print('VALIDATION',sum(checks.values()),'checks passed;',len(ts),'timeseries rows;',len(dates),'distinct series',flush=True)
if __name__=='__main__':run()
