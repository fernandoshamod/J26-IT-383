"""Verify and package the seven review deliverables; no scenario generation."""
import json, zipfile
import openpyxl
import pandas as pd
from common import ROOT,REPORTS,COLLECTION

names=['simulation_assumption_register.xlsx','financial_dependency_rules.md','scenario_generation_design.md',
       'risk_label_definition.md','spatial_financial_graph_schema.md','simulation_validation_plan.md','missing_real_world_data_checklist.md']
for name in names:
    p=REPORTS/name
    assert p.exists() and p.stat().st_size>100,p
meta=json.loads((REPORTS/'simulation_review_data.json').read_text(encoding='utf-8'))
wb=openpyxl.load_workbook(REPORTS/names[0],read_only=False,data_only=True)
sheet=wb['Assumptions']
values=list(sheet.values)
assert list(values[0])==meta['Assumptions']['headers']
assert len(values)==35
assert len({r[0] for r in values[1:]})==34
assert all(r[11]=='Pending review' for r in values[1:])
assert [wb['Review'][f'B{r}'].value for r in range(5,10)]==[34,34,0,0,0]
assert len(sheet.data_validations.dataValidation)==1
evidence=list(wb['Observed_Evidence'].values)
assert len(evidence)==11
capacity=pd.read_csv(ROOT/'data/processed/venues.csv').capacity
assert evidence[1][3:9]==(len(capacity),capacity.min(),capacity.quantile(.25),capacity.median(),capacity.quantile(.75),capacity.max())
for s in wb:
    for row in s:
        assert all(c.data_type!='e' for c in row),s.title
wb.close()
with zipfile.ZipFile(COLLECTION/'Component4_Simulation_Review_Package.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(REPORTS/name,name)
print('PASS: 7 deliverables; 34 pending rows; source capacity reconciled; cached counts restored; dropdown present; no Excel error cells.')
print('PACKAGE',COLLECTION/'Component4_Simulation_Review_Package.zip')
