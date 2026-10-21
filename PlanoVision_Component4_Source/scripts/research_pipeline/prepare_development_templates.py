"""Create blank collection/config templates and explicit two-type TEST fixtures."""
import sys,json,csv,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from component4.engine import PARAMS,RATE_UNITS,FORMULA_IDS,evaluate,what_if
ROOT=Path(__file__).resolve().parents[2]
REPORTS=ROOT/'reports'

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

tables={
 'Events':['Event_ID','Event_Type','Planning_Date','Event_Date','Planned_Guests','Seat_Share','VIP_Seats','Event_Hours','Setup_Hours','Clearance_Hours','Initial_Budget_LKR','Expected_Retained_Receipts_LKR','Revenue_Mode','Minimum_Margin_Points','Reserve_Ratio','Evidence_Kind','Evidence_Ref','Consent_or_Permission_Ref'],
 'Vendor_Quotes':['Quote_ID','Vendor_Pseudonym','Service_Category','Quote_Date','Valid_Until','Currency','Tax_Scope','Tax_Rate_Points','Included_Service_IDs','Excluded_Service_IDs','Minimum_Charge_LKR','Overtime_Terms','Evidence_Kind','Evidence_Ref','Permission_Status'],
 'Quote_Lines':['Quote_Line_ID','Quote_ID','Event_ID','Engine_Item_ID','Service_Description','Quantity','Quantity_Unit','Rate','Rate_Unit','Currency','Tax_Scope','Tax_Rate_Points','Included_In_Line_ID','Fixed_Charge_LKR','Discount_Terms','Quoted_Total_LKR','Approval_Status','Evidence_Ref'],
 'Venue_Layout':['Venue_ID','Event_ID','Arrangement','Measured_Venue_Area_m2','Excluded_Non_Event_Area_m2','Usable_Area_m2','Approved_Capacity_Persons','Capacity_Source','Stage_Width_m','Stage_Length_m','Area_Per_Standard_Seat_m2','Area_Per_VIP_Seat_m2','Service_Area_m2','Circulation_Area_m2','Furniture_Included','Layout_Origin','Measurement_Date','Floor_Plan_Ref','Practitioner_Review_Ref'],
 'Staffing':['Staff_Plan_ID','Event_ID','Role','Staff_Count','Base_Staff','Guests_Per_Staff','Stage_or_Service_Extras','Paid_Event_Hours','Paid_Setup_Hours','Paid_Clearance_Hours','Regular_Hours_Limit','Overtime_Multiplier','Hourly_Rate_LKR','Rate_Date','Tax_Scope','Tax_Rate_Points','Included_In_Vendor_Package','Package_Quote_ID','Scope_Exclusions','Evidence_Ref','Approval_Status'],
 'Formal_Approvals':['Review_Record_ID','Assumption_ID','Event_Type','Formula_Version','Parameter_Config_Hash','Reviewer_Name','Reviewer_Role','Review_Date','Decision','Rationale','Evidence_Refs','Approved_Min','Approved_Max','Approval_Kind']}
for name,headers in tables.items():
    p=ROOT/'data/manual_templates'/f'{name}.csv';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8-sig') as f:csv.writer(f).writerow(headers)
save(REPORTS/'quotation_template_metadata.json',tables)
approval={'status':'pending','reviewer':None,'reviewer_role':None,'reviewed_at':None,'rationale':None,'evidence_ref':None}
config={'config_version':'0.1.0-template','rules_version':'0.1.0-review','record_kind':'unapproved_configuration_template','currency':'LKR','seed':None,
        'source_snapshot_hashes':None,'calibration_cutoff':None,'formula_approvals':{a:copy.deepcopy(approval) for a in FORMULA_IDS},
        'pilot':{'scenario_count':None,'explicit_user_authorization':False,'approved_config_sha256':None,'review_record_ref':None,'passing_test_report_ref':None,'sampling_protocol_ref':None,'provenance_protocol_ref':None,'generator_implementation_verified':False},'archetypes':{}}
for event in ['Wedding','Corporate']:
    config['archetypes'][event]={'parameters':{p:None for p in PARAMS},'parameter_approval':{**approval,'parameter_hash':None},
        'approved_override_bounds':{p:{'min':None,'max':None} for p in PARAMS},
        'rates':{item:{'rate':None,'unit':unit,'currency':'LKR','quote_date':None,'tax_scope':None,'tax_rate_points':None,'evidence_ref':None,'approval_status':'pending'} for item,unit in RATE_UNITS.items()},
        'billing':{'catering_mode':None,'staff_scope':None,'included_items':None},'av_steps':None,'lighting_steps':None,
        'outcome_uncertainty':{'distribution':None,'cost_bounds':None,'revenue_bounds':None,'dependence_spec':None,'approval_ref':None},
        'injected_vendor_regime':{'prevalence':None,'multiplier_bounds':None,'affected_services':None,'approval_ref':None},
        'sampling_weights':None,'geometry_origin':None,'revenue_mode':None,'date_bounds':None,'vendor_tiers':None,'price_series_whitelist':None}
save(ROOT/'config/simulator.v0.1.template.json',config)
fixture=copy.deepcopy(config);fixture['record_kind']='mock_test_fixture';fixture['config_version']='0.1.0-mock-test-only'
values=[100,1,0,10,0,4,1,1,450,50,1.2,1.8,4,3,20,30,200,2,25,0,8,1.5,1000000,1200000,20,.1]
assert len(values)==len(PARAMS)
test_rates={'catering':1000,'chairs':100,'tables':500,'stage':100,'av':5000,'lighting':2000,'labour':200,'venue_fixed':10000,'venue_hourly':1000,'security':3000,'decoration':2000,'transport':1000,'misc':500,'equipment_other':1000}
for event in fixture['archetypes']:
    profile=fixture['archetypes'][event];profile['parameters']=dict(zip(PARAMS,values))
    if event=='Corporate':profile['parameters'].update(guest_count=60,event_hours=6)
    profile['billing']={'catering_mode':'package','staff_scope':'general_staff_excludes_vendor_packages','included_items':{}}
    profile['av_steps']=[{'max_stage_area_m2':20,'units':1},{'max_stage_area_m2':50,'units':2}]
    profile['lighting_steps']=[{'max_stage_area_m2':30,'units':1},{'max_stage_area_m2':50,'units':2}]
    for item,rate in test_rates.items():profile['rates'][item].update(rate=rate,quote_date='2026-10-01',tax_scope='inclusive',tax_rate_points=0,evidence_ref='MOCK-UNIT-TEST-NOT-A-VENDOR-QUOTE',approval_status='mock_test_only')
save(ROOT/'fixtures/config.mock_test_only.json',fixture)
for event in ['Wedding','Corporate']:
    save(ROOT/f'api/mock/{event.lower()}.response.mock.json',evaluate(fixture,event,mode='mock_test_fixture'))
save(ROOT/'api/mock/what_if.response.mock.json',what_if(fixture,'Wedding',{'guest_count':150},mode='mock_test_fixture'))
save(ROOT/'api/mock/blocked.response.json',evaluate(config,'Wedding'))
print('Created blank collection tables, null numerical config, and clearly marked test/API fixtures. No event dataset generated.')
