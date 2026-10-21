import csv, hashlib, json, sys, math
from pathlib import Path
from collections import Counter
from datetime import date,time
import pandas as pd
R=Path(r'D:\Vendor-Intelligence-System'); O=R/'research_data_v2/yelp_lineage_gap_audit'; Y=Path(r'D:\Yelp-JSON (1)\Yelp JSON\yelp_dataset')
sys.dont_write_bytecode=True
sys.path.insert(0,str(R))
from backend.engine.package_data_loader import load_service_options
from backend.engine.validation_helpers import validate_service_option_lkr
from backend.engine.dynamic_package_service import generate_dynamic_packages
from backend.schemas.dynamic_package_request import DynamicPackageRequest
def writecsv(name,rows):
 with (O/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def inv(p,selected=None):
 h=hashlib.sha256();n='';schema=[];matches={}
 if p.suffix=='.json' and p.name.startswith('yelp_academic'):
  n=0
  with p.open('rb') as f:
   for line in f:
    h.update(line);n+=1
    if n==1 or selected is not None:
     obj=json.loads(line)
     if n==1:schema=list(obj)
     if selected is not None and obj.get('business_id') in selected:matches[obj['business_id']]=obj
 else:
  with p.open('rb') as f:
   for block in iter(lambda:f.read(4194304),b''):h.update(block)
  if p.suffix=='.csv':
   with p.open(encoding='utf-8-sig',newline='') as f:
    q=csv.reader(f);schema=next(q);n=sum(1 for _ in q)
 return dict(path=str(p),bytes=p.stat().st_size,rows=n,schema=';'.join(schema),sha256=h.hexdigest(),status='present'),matches
P=pd.read_csv(R/'hybrid_simulation_v1/real_vendor_profiles.csv',dtype={'business_id':'string'});T=load_service_options();ids=set(P.business_id.dropna().astype(str))
names=['vendor_recommendation_dataset_ids_checked.csv','review_summary_verification.csv','vendor_compatibility_matrix.csv','vendor_availability.csv','venue_constraints.csv','event_requirements.csv','hybrid_simulation_v1/real_vendor_profiles.csv','hybrid_simulation_v1/synthetic_service_options.csv','hybrid_simulation_v1/synthetic_event_requirements.csv','hybrid_simulation_v1/synthetic_availability.csv','hybrid_simulation_v1/synthetic_collaboration_scenarios.csv','hybrid_simulation_v1/hybrid_vendor_service_dataset.csv','hybrid_simulation_v1/field_provenance.csv','hybrid_simulation_v1/dataset_manifest.json','build_hybrid_dataset.py','backend/engine/candidate_selection.py','backend/engine/bounded_package_generator.py','backend/engine/validation_helpers.py','backend/engine/dynamic_feasibility.py','backend/engine/package_data_loader.py','backend/engine/service_compatibility.py','notebooks/01_vendor_dataset_audit.ipynb']
files=[Y/'yelp_academic_dataset_business.json',Y/'yelp_academic_dataset_review.json',Y/'Dataset_User_Agreement.pdf']+[R/x for x in names]
inventory=[];matches={}
for i,p in enumerate(files):
 print('inventory',i+1,len(files),p.name,flush=True)
 if p.exists():
  row,found=inv(p,ids if i==0 else None);inventory.append(row)
  if found:matches=found
 else:inventory.append(dict(path=str(p),bytes='',rows='',schema='',sha256='',status='MISSING'))
writecsv('source_inventory.csv',inventory)
diff=Counter()
for row in P.to_dict('records'):
 src=matches.get(str(row['business_id']))
 if not src:continue
 for field in ['name','city','state','latitude','longitude','stars','review_count','is_open','categories','attributes','hours']:
  val=row.get(field);orig=src.get(field)
  if field in ('attributes','hours') and isinstance(val,str):
   try:val=json.loads(val)
   except ValueError:pass
  if isinstance(val,dict):equal=val==orig
  elif pd.isna(val):equal=orig is None
  elif field in ('latitude','longitude','stars','review_count','is_open') and orig is not None:equal=float(val)==float(orig)
  else:equal=val==orig
  if not equal:diff[field]+=1
services=[]
for service,f in T.groupby('service_category'):
 services.append(dict(service_category=service,option_rows=len(f),distinct_vendors=f.business_id.nunique(),distinct_locations=f[['simulated_service_city','simulated_service_state']].drop_duplicates().shape[0],corporate_rows=int(f.supported_event_types.fillna('').str.contains('Corporate',case=False).sum()),capacity_known_rows=int(f.max_guests.notna().sum()),capacity_ge_50_rows=int(f.max_guests.ge(50).sum()),capacity_ge_500_rows=int(f.max_guests.ge(500).sum()),positive_unit_price_rows=int(f.unit_price.gt(0).sum()),pricing_bases=';'.join(sorted(f.pricing_basis.dropna().unique())),min_unit_price_usd=f.unit_price.min(),median_unit_price_usd=f.unit_price.median()))
for guests in (50,500):
 for record in services:
  frame=T.loc[T.service_category.eq(record['service_category'])]
  priced=[]
  for item in frame.to_dict('records'):
   result=validate_service_option_lkr(item,guests,4,1000000)
   value=result.get('estimated_cost_lkr')
   if value is not None and math.isfinite(float(value)) and result.get('capacity_status')!='Fail':
    priced.append(float(value))
  record[f'priceable_{guests}_rows']=len(priced)
  record[f'affordable_{guests}_rows']=sum(v<=1000000 for v in priced)
  record[f'min_estimated_{guests}_lkr']=min(priced,default=None)
  record[f'median_estimated_{guests}_lkr']=pd.Series(priced).median() if priced else None
writecsv('coverage_by_service.csv',services)
locations=[]
for (city,state),f in T.groupby(['simulated_service_city','simulated_service_state'],dropna=False):
 c=f[f.service_category.eq('Catering')];e=f[f.service_category.eq('Entertainment')]
 locations.append(dict(city=city,state=state,option_rows=len(f),distinct_vendors=f.business_id.nunique(),service_categories=';'.join(sorted(set(f.service_category))),category_count=f.service_category.nunique(),catering_options=len(c),catering_vendors=c.business_id.nunique(),catering_500_options=int(c.max_guests.ge(500).sum()),catering_500_vendors=c[c.max_guests.ge(500)].business_id.nunique(),entertainment_options=len(e),entertainment_vendors=e.business_id.nunique(),has_both=bool(len(c) and len(e))))
writecsv('coverage_by_location.csv',locations)
def norm(x):return str(x).strip().casefold()
scenarios=[]
for city,state,guests in [('Bensalem','PA',50),('Bensalem','PA',500),('Belle Chasse','LA',50)]:
 req=DynamicPackageRequest(event_type='Corporate',event_date=date(2027,1,1),start_time=time(14),end_time=time(18),city=city,state=state,guest_count=guests,budget_lkr=1000000,required_services=['Catering','Entertainment'])
 response=generate_dynamic_packages(req);stages={}
 for service in req.required_services:
  f=T[T.service_category.eq(service)&T.simulated_service_city.map(norm).eq(norm(city))&T.simulated_service_state.map(norm).eq(norm(state))]
  ev=f.loc[f.supported_event_types.fillna('').map(lambda x:'corporate' in [norm(z) for z in x.split(';')])]
  cap=ev.loc[ev.max_guests.ge(guests)] if service=='Catering' else ev;priced=[]
  for item in cap.to_dict('records'):
   result=validate_service_option_lkr(item,guests,4,1000000);cost=result.get('estimated_cost_lkr')
   if cost is not None and math.isfinite(float(cost)) and result.get('capacity_status')!='Fail':priced.append((str(item['business_id']),float(cost),item['service_option_id']))
  stages[service]=dict(location_rows=len(f),location_vendors=f.business_id.nunique(),event_type_rows=len(ev),capacity_rows=len(cap),capacity_vendors=cap.business_id.nunique(),priceable_rows=len(priced),priceable_vendors=len(set(x[0] for x in priced)),individually_affordable_rows=sum(x[1]<=1000000 for x in priced),min_cost_lkr=min((x[1] for x in priced),default=None),min_option=min(priced,key=lambda x:x[1]) if priced else None,capacity_distribution=dict(Counter(str(x) for x in f.max_guests.dropna())) if service=='Catering' else {})
 scenarios.append(dict(city=city,state=state,guests=guests,stages=stages,generation={k:v for k,v in response['generation'].items() if k!='packages'}|{'package_count':len(response['generation']['packages'])},diagnostics=response.get('diagnostics')))
metrics=dict(business_rows=inventory[0]['rows'],review_rows=inventory[1]['rows'],profile_rows=len(P),profile_distinct_ids=len(ids),source_matched_ids=len(matches),source_unmatched_ids=len(ids-set(matches)),source_field_differences=dict(diff),option_rows=len(T),option_distinct_ids=T.service_option_id.nunique(),option_missing_profile_ids=len(set(T.business_id.astype(str))-ids),profiles_without_options=len(ids-set(T.business_id.astype(str))),locations=len(locations),locations_with_both=sum(x['has_both'] for x in locations),scenarios=scenarios)
(O/'audit_metrics.json').write_text(json.dumps(metrics,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in metrics.items() if k!='scenarios'},indent=2),flush=True)
for s in scenarios:
 g=s['generation'];print(s['city'],s['guests'],s['stages'],g['status'],g['package_count'],g['search'],flush=True)



