import json
import pandas as pd
from common import ROOT,REPORTS

UNITS={
 'Inflation':{'Month':'ISO month-start date','Base_Year':'year','Index_Value':'index, base 2021','MoM_Pct':'percentage points','YoY_Pct':'percentage points','Moving_12M_Pct':'percentage points'},
 'Retail_Prices':{'Year':'year','Month':'month number','Week_In_Month':'publisher week number','YoY_Pct':'percentage points','WoW_Pct':'percentage points'},
 'Venues':{'Capacity':'persons (advertised capacity, not area)','ZIP':'postal identifier'},
 'Events':{'Arrive Date':'MM/DD/YYYY date','Depart Date':'MM/DD/YYYY date','Attendance':'publisher attendance count; planning/actual status unspecified'},
 'UK_Service_Awards':{'Award_Value':'units of Currency column (contract total)','Currency':'ISO currency code','Award_Date':'publisher award date'},
 'SL_Procurement':{'Procurement_Count':'procurement count','Awarded_Value_LKR_Million':'LKR million; average or period total per Value_Basis'},
 'USDA_Away':{'price':'USD per restaurant product','standard_error':'USD per product','number_obs':'count','year':'year','quarter':'quarter'},
 'USDA_Home_National':{'Unit_value_mean_wtd':'USD per 100 grams','Unit_value_mean_unwtd':'USD per 100 grams','Unit_value_se_wtd':'USD per 100 grams','Purchase_dollars_wtd':'weighted USD expenditure','Purchase_dollars_unwtd':'unweighted USD expenditure','Purchase_grams_wtd':'weighted grams','Purchase_grams_unwtd':'unweighted grams','Number_stores':'count','Price_index_GEKS':'GEKS price index, publisher base','Year':'year','Month':'month number'},
 'USDA_Home_Supplement':{'Year':'year','Month':'month number'},
 'CBSL_Prices_Wages':{'Numeric_Value':'table-specific unit; header interpretation required','Text_Value':'source heading/text; not quantitative observation','Source_Row':'source row coordinate','Source_Column':'source column coordinate'}
}
def run():
    d=pd.read_csv(REPORTS/'source_mapping.csv').fillna('')
    for i,r in d.iterrows():
        unit=UNITS.get(r.Dataset_Name,{}).get(r.Original_Column)
        if r.Dataset_Name=='Retail_Prices' and 'Price_LKR' in r.Original_Column:unit='LKR per Unit_Raw'
        if r.Original_Column in {'Source_ID','Source_File','Source_Cell','Source_Sheet','OCID','Tender_ID','Award_ID','EFPG_code','Metroregion_code'}:unit='identifier / locator'
        if r.Original_Column=='PDF_Page':unit='PDF page locator'
        if unit:d.loc[i,'Original_Unit']=unit
    d.to_csv(REPORTS/'source_mapping.csv',index=False)
    dictionary=pd.read_csv(REPORTS/'updated_data_dictionary.csv').fillna('')
    schema=pd.read_csv(ROOT/'outputs/01a12103-7a09-7331-bb93-9e24a6f05005/processed_csv/Schema_Mapping.csv').fillna('')
    gaps=schema[['Master_Field','Availability','Source_Fields','Transformation_Or_Gap','Model_Use']]
    (REPORTS/'mapping_workbook_data.json').write_text(json.dumps({'Source_Mapping':{'headers':list(d),'rows':json.loads(d.to_json(orient='values'))},
                                                                'Master_Field_Review':{'headers':list(gaps),'rows':json.loads(gaps.to_json(orient='values'))}},ensure_ascii=False),encoding='utf-8')
    print('MAPPING_ROWS',len(d))
if __name__=='__main__':run()
