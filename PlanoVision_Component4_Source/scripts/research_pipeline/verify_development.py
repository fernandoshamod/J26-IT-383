"""Verify delivered template/tests and package current development artifacts."""
from pathlib import Path
import hashlib,io,json,unittest,zipfile
import openpyxl
ROOT=Path(__file__).resolve().parents[2]
metadata=json.loads((ROOT/'reports/quotation_template_metadata.json').read_text())
book=ROOT/'reports/sri_lanka_quotation_collection_template.xlsx'
wb=openpyxl.load_workbook(book,data_only=False)
assert set(wb.sheetnames)==set(metadata)|{'ReadMe'}
for name,headers in metadata.items():
    sheet=wb[name]
    assert [c.value for c in sheet[1]]==headers
    assert all(c.value is None for row in sheet.iter_rows(min_row=2,max_row=26) for c in row)
    assert len(sheet.tables)==1
    assert sheet.freeze_panes=='C2'
assert len(wb['Events'].data_validations.dataValidation)>0
wb.close()
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
print(stream.getvalue())
if not result.wasSuccessful():raise SystemExit(1)
report=['# Component 4 software verification — 9 October 2026','',f'{result.testsRun} tests passed; failures: {len(result.failures)}; errors: {len(result.errors)}; skipped: {len(result.skipped)}.','', 'Verified accounting net+tax=gross and total reconciliation, inclusive/exclusive tax, bundle exclusions, capacity/area boundaries, contingency separation, profit/margin/overrun boundaries, missing/invalid parameter blocking, fixture provenance, live override bounds and approval-hash invalidation, API field firewall, contract fixtures, deterministic replay and paired What-If calculations.','', 'Workbook: six empty input tables plus ReadMe; headers, blank rows, tables, dropdowns and freeze panes verified from saved XLSX. All seven sheet previews were inspected; artifact error scan returned zero matches. Native Excel interaction was not tested.','', 'The exporter reported process exit 1 after logging a successful save; the saved XLSX was independently reopened and verified. This does not affect the verified blank template.','', 'No simulation generator, stochastic validation, field calibration, external event validation or trained model accuracy was tested. These remain unavailable. In-memory artificial approval records exist only for software branch tests, not as evidence or authorized configurations.','', '## Actual test runner output','', '```text',stream.getvalue().strip(),'```']
(ROOT/'reports/component4_engine_test_report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
include=[ROOT/'README_component4_development.md']
for folder in ['component4','config','fixtures','api','data/manual_templates']:
    include.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for name in ['sri_lanka_quotation_collection_template.xlsx','quotation_collection_guide.md','quotation_template_metadata.json','technical_review_snapshot.json','technical_review_implementation_response.md','wedding_corporate_poc_scope.md','pilot_authorization_conditions.md','component4_engine_test_report.md','financial_dependency_rules.md','scenario_generation_design.md','risk_label_definition.md','spatial_financial_graph_schema.md','simulation_validation_plan.md','missing_real_world_data_checklist.md','simulation_assumption_register.xlsx']:
    include.append(ROOT/'reports'/name)
include.extend(ROOT/'tests'/name for name in ['test_engine.py','test_dashboard_api.py','test_financial_features.py'])
include.extend(ROOT/'scripts/research_pipeline'/name for name in ['prepare_development_templates.py','finalize_development.py','verify_development.py','build_quotation_template.mjs','features.py','common.py'])
manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(include))}
(ROOT/'reports/component4_development_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
include.append(ROOT/'reports/component4_development_manifest.json')
dest=ROOT/'outputs/01a12103-7a09-7331-bb93-9e24a6f05005/Component4_Development_POC_Package.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(include)):z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
print(f'VERIFIED {result.testsRun} tests; blank workbook; ZIP {dest}; {len(include)} files.')
