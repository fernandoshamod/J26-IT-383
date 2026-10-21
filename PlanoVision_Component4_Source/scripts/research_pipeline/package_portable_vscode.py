"""Package the current runnable dashboard and verified dependency closure."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import tempfile
import zipfile
import argparse
from component4.release_input import sha256


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence-release',action='store_true');parser.add_argument('--completion-release',action='store_true');parser.add_argument('--gap-closure-release',action='store_true');parser.add_argument('--component2-bridge-release',action='store_true');parser.add_argument('--lkr-graph-local-ai-release',action='store_true');parser.add_argument('--pp1-final-release',action='store_true')
    parser.add_argument('--backend-crud-release',action='store_true')
    parser.add_argument('--dev-project-release',action='store_true')
    parser.add_argument('--crud-flow-release',action='store_true')
    parser.add_argument('--data-quality-release',action='store_true')
    parser.add_argument('--ui-refresh-release',action='store_true')
    parser.add_argument('--pp1-submission-release',action='store_true')
    args=parser.parse_args()
    args.ui_refresh_release=args.ui_refresh_release or args.pp1_submission_release
    args.data_quality_release=args.data_quality_release or args.ui_refresh_release
    args.crud_flow_release=args.crud_flow_release or args.data_quality_release
    args.dev_project_release=args.dev_project_release or args.crud_flow_release
    args.backend_crud_release=args.backend_crud_release or args.dev_project_release
    args.pp1_final_release=args.pp1_final_release or args.backend_crud_release
    ai=args.lkr_graph_local_ai_release or args.pp1_final_release
    bridge=args.component2_bridge_release or ai
    suffix='_PP1_Submission_20261021' if args.pp1_submission_release else '_UIRefresh_20261021' if args.ui_refresh_release else '_DataQuality_20261021' if args.data_quality_release else '_CRUDConnected_20261020' if args.crud_flow_release else '_VSCodeDev_20261020' if args.dev_project_release else '_BackendCRUD_20261020' if args.backend_crud_release else '_PP1_Final_20261020' if args.pp1_final_release else '_LKRGraphLocalAI_20261019' if ai else '_Component2Bridge_20261018' if bridge else '_GapClosure_20261018' if args.gap_closure_release else '_Complete_Ready' if args.completion_release else '_ModelEvidence_Final' if args.evidence_release else ''
    destination=ROOT/f'outputs/PlanoVision_Component4_VSCode_v3.1_20261016{suffix}.zip'
    if destination.exists():raise ValueError('refuse_existing_portable_archive')
    mappings={}
    def add(relative):
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('missing_or_unsafe_package_source:'+relative)
        mappings[relative]=path
    def tree(relative):
        base=ROOT/relative
        for p in base.rglob('*'):
            if p.is_file() and not any(x in ('node_modules','__pycache__','.git','.venv') for x in p.parts):add(p.relative_to(ROOT).as_posix())
    if args.ui_refresh_release:
        add('reports/UI_REFRESH_20261021.md')
        for name in ('PP1_READY_LITERATURE_AND_GAP_20261021.md','RESEARCH_GAP_AND_RELATED_WORK_20261021.md','RESEARCH_GAP_SEARCH_AUDIT_20261021.md'):add('reports/'+name)
    if args.pp1_submission_release:
        add('reports/PP1_COMPONENT_COMPLETE_DOSSIER_20261021.md')
        add('reports/UI_REFRESH_FINAL_VERIFICATION_20261021.json')
        for name in ('README.md','README_component4_development.md','README_dataset_pipeline.md','README_LKR_RESEARCH.md','README_MANUAL_MODEL_CHECK.md','README_SERVICE_PLANNER.md'):
            add(name)
        for name in ('published_lkr_rate_evidence.csv','sl_procurement_context.csv','provider_terms.csv'):
            add('data/hybrid/Component4_Hybrid_Dataset_Final_v1.0/prepared/benchmarks/'+name)
        add('data/hybrid/Component4_Hybrid_Dataset_Final_v1.0/prepared/real/weekly_retail_observations.csv')
        add('data/processed/retail_prices.csv')
    modules=['__init__','engine','release_input','lkr_research','lkr_inference','planner_services','planner_insights',
        'planner_dashboard_api','planner_dashboard_http','dashboard_evidence','pricing_disclosure','component2_adapter','forecast_bridge','expense_risk','expense_risk_inference','enhanced_risk_inference',
        'model_explanations','risk_experiment','risk_enhancement','model_diagnostics','frozen_robustness','planner_input']
    for name in modules:add('component4/'+name+'.py')
    if args.dev_project_release:
        tree('backend');tree('scripts/dev')
        for name in ('package.json','package-lock.json','README_VSCODE_DEV.md'):add(name)
    if args.crud_flow_release:
        add('reports/CRUD_CONNECTED_VERIFICATION_20261020.md')
        add('reports/crud_connected_report_20261020.png')
    if args.data_quality_release:
        add('reports/DATA_QUALITY_FIX_20261021.md');tree('reports/data_quality_fix_20261021')
        for name in ('historical_source_review','reviewed_price_quality'):add('component4/'+name+'.py')
        for name in ('review_historical_sources','audit_current_monetary_data'):add('scripts/research_pipeline/'+name+'.py')
        for name in ('test_historical_source_review','test_reviewed_price_quality'):add('tests/'+name+'.py')
    if args.backend_crud_release:
        add('component4/planner_records.py')
        add('tests/test_planner_records.py')
        add('reports/BACKEND_SQLITE_CRUD_20261020.md')
        add('reports/backend_sqlite_save_20261020.png')
    if args.pp1_final_release:
        add('component4/planner_calculation_scope.py')
        add('config/planner_calculator_scope.v0.1.json')
        add('tests/test_planner_calculation_scope.py')
        for name in ('BOOKING_DETAILS_AND_MOVE_20261020.md','BOOKING_DATE_POLICY_FIX_20261020.md','PLANNER_SIZE_SCOPE_20261019.md','PP1_FINAL_RELEASE_20261020.md'):
            add('reports/'+name)
        add('reports/pp1_final_calendar_details_20261020.png')
        tree('reports/pp1_demo_check_20261020T135223Z')
    if ai:
        add('component4/reviewed_price_quality.py')
        tree('data/reviewed/historical_quality_v0_3_20261021')
        for name in ('lkr_graph','lkr_graph_inference','graph_experiment','local_llm_report','local_llm_runtime','future_price_forecast'):add('component4/'+name+'.py')
        for name in ('lkr_graph.v0.1','future_price_deployment.v0.1'):add('config/experiments/'+name+'.json')
        add('config/llm_report.v0.1.json')
        add('scripts/model_experiments/train_lkr_graph.py')
        for name in ('fetch_ollama_cpu','setup_local_ai','verify_local_ai_integration'):add('scripts/research_pipeline/'+name+'.py')
        add('tests/test_lkr_graph_and_llm.py')
        tree('outputs/experiments/v4.0/lkr_graph_v0_1_20261018')
        tree('reports/experiments/v4.0/lkr_graph_v0_1_20261018')
        tree('outputs/experiments/v1.2/future_prices_20261018_v0_1')
        add('reports/FUTURE_PRICE_DEPLOYMENT_20261018.md')
        add('reports/LKR_GAT_LOCAL_AI_COMPLETION_20261019.md')
        for name in ('lkr_gat_live_inference_20261019.png','local_ai_report_live_20261019.png'):add('reports/'+name)
        actual=ROOT/'reports/lkr_graph_local_ai_20261018/actual_runtime_verification.json'
        if json.loads(actual.read_text())['status']!='PASS_ACTUAL_LOCAL_RUNTIME_INTEGRATION':raise ValueError('actual_local_llm_verification_required')
        tree('reports/lkr_graph_local_ai_20261018')
        runtime='work/ollama_cpu_0_40_5/'
        native=json.loads((ROOT/(runtime+'DOWNLOAD_MANIFEST.json')).read_text())
        for name in native['files']:add(runtime+name)
        add(runtime+'DOWNLOAD_MANIFEST.json');add(runtime+'LICENSE.Ollama.txt')
    for name in ('lkr_research.v2.0','expense_risk.v3.0','risk_enhancement.v3.1','model_diagnostics.v0.1','robustness.v0.1'):add('config/'+name+'.json')
    for version,run in (('v2.0','lkr_research_v2_0_20261014'),('v3.0','expense_risk_v3_0_20261015'),('v3.1','expense_risk_v3_1_20261016')):
        for branch in ('data','outputs','reports'):tree(f'{branch}/experiments/{version}/{run}')
        inventory=json.loads((ROOT/f'reports/experiments/{version}/{run}/checksums.json').read_text())
        for name,digest in inventory.items():
            add(name)
            if sha256(ROOT/name)!=digest:raise ValueError('original_artifact_integrity_failure:'+name)
        protocol=json.loads((ROOT/f'outputs/experiments/{version}/{run}/protocol.json').read_text())
        for name,digest in protocol.get('source_hashes',{}).items():
            add(name)
            if sha256(ROOT/name)!=digest:raise ValueError('original_numerical_source_changed:'+name)
    config=json.loads((ROOT/'config/lkr_research.v2.0.json').read_text());add(config['source_file'])
    tree('frontend/src');tree('frontend/dist')
    for name in ('index.html','package.json','package-lock.json','tsconfig.json','vite.config.ts','.gitignore'):add('frontend/'+name)
    for name in ('launch_financial_dashboard','check_expense_model','verify_portable_package','verify_demo_acceptance'):add('scripts/research_pipeline/'+name+'.py')
    for name in ('audit_errors_and_learning_curves','run_frozen_robustness'):add('scripts/model_experiments/'+name+'.py')
    for name in ('test_expense_risk','test_expense_risk_inference','test_risk_enhancement','test_model_diagnostics','test_frozen_robustness','test_planner_input','test_planner_dashboard','test_dashboard_evidence','test_dashboard_launcher','test_pricing_disclosure','test_planner_services'):add('tests/'+name+'.py')
    if (ROOT/'tests/__init__.py').exists():add('tests/__init__.py')
    add('fixtures/planner_services.mock_test_only.json')
    tree('reports/diagnostics/v3_1_steps1_2_20261016');tree('reports/robustness/v3_1_frozen_robustness_20261016')
    add('reports/public_hotel_benchmark_test_results.json')
    if args.completion_release or args.gap_closure_release:add('reports/final_demo_acceptance_20261016.json')
    if args.gap_closure_release:
        for name in ('GAP_CLOSURE_20261018.md','PP1_DEMO_TEST_GUIDE.md','PP1_VIVA_QA_NOTES.md','gap_closure_save_restore_20261018.jpg','gap_closure_price_scope_20261018.jpg'):add('reports/'+name)
    if bridge:
        for name in ('COMPONENT2_FORECAST_BRIDGE_20261018.md','GAP_CLOSURE_20261018.md','PP1_DEMO_TEST_GUIDE.md','PP1_VIVA_QA_NOTES.md','component2_import_preview_20261018.jpg','forecast_coverage_blocker_20261018.jpg','historical_forecast_replay_20261018.jpg'):add('reports/'+name)
        for name in ('component2_quotation_bundle.schema.json','component2_quotation_bundle.ts'):add('api/contracts/'+name)
        add('fixtures/component2_quotation_bundle.mock_test_only.json')
        add('tests/test_component2_forecast_bridge.py')
        add('scripts/research_pipeline/export_component2_contract.py')
        for name in ('selected_models.json','heldout_forecasts.csv','experiment_protocol.json'):
            add('outputs/experiments/v1.0/prophet_historical_v0_1_native_20261012/'+name)
    template=ROOT/'packaging/portable'
    for name in ('START_PLANOVISION.cmd','Setup_Windows.cmd','Run_Financial_Dashboard.cmd','Run_Trained_Expense_Model_Check.cmd','Verify_Package.cmd','requirements.txt','README.md'):
        mappings[name]=template/name
    if ai:
        mappings['Setup_Local_AI.cmd']=template/'Setup_Local_AI.cmd'
        mappings['requirements-lkr-graph-cpu.txt']=ROOT/'config/requirements/lkr_graph_cpu.txt'
    mappings['README_FINANCIAL_DASHBOARD.md']=template/'README.md'
    for target in ('settings','launch','tasks','extensions'):mappings['.vscode/'+target+'.json']=template/('vscode-'+target+'.json')
    protected={str(p.relative_to(ROOT)):sha256(p) for p in set(mappings.values())}
    payloads={}
    for name,path in sorted(mappings.items()):
        data=path.read_bytes()
        if name.endswith('.cmd'):data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        payloads[name]=data
    payloads['.gitignore']=b'.venv/\n**/__pycache__/\nfrontend/node_modules/\nwork/\nruntime/\n'
    if ai:
        payloads['requirements.txt']+=b'\n-r requirements-lkr-graph-cpu.txt\n'
        payloads['README.md']+=b'\n\n## LKR GAT + local AI release (2026-10-19)\n\nRun Setup_Windows.cmd to install pinned Python CPU dependencies, then Setup_Local_AI.cmd once to download the local Qwen model (about 986 MB). Start with START_PLANOVISION.cmd. Reports & explainability contains the new LKR GAT comparator and Generate local AI draft. No cloud account or API key. CPU runtime files are included; local LLM weights and machine Python environments are not. The source workspace verification used the actual downloaded model. Fresh pip installation is not claimed by extracted-tree tests. Read reports/LKR_GAT_LOCAL_AI_COMPLETION_20261019.md.\n'
        payloads['README_FINANCIAL_DASHBOARD.md']=payloads['README.md']
    if args.pp1_final_release:
        payloads['README.md']+=b'\n\n## Final PP1 update - 20 October 2026\n\nThis release includes the latest blank event setup, calculator scope, saved calendar, client names, top Close button, rescheduling and recoverable deletion. Reserved dates appear red without an expanded booking list. Calendar records and main plans live only in browser storage for the exact host/port. Export booking and main-plan backups before switching browser, port or machine. Existing personal browser records are NOT included in this archive. See reports/PP1_FINAL_RELEASE_20261020.md for final verification scope and limitations. No dataset regeneration or model fitting is required.\n'
        payloads['README_FINANCIAL_DASHBOARD.md']=payloads['README.md']
    if args.backend_crud_release:
        payloads['README.md']+=b'\n\n## Backend SQLite CRUD update - 20 October 2026\n\nFinancial planner includes Save event to backend, Refresh backend events, Load, Update and confirmed Delete. Calendar reservations now use the backend database, with explicit import for previous browser bookings. Production data lives in runtime/planner.sqlite3. This personal database is NOT bundled or committed. Keep it when upgrading folders and back it up with the server stopped. See reports/BACKEND_SQLITE_CRUD_20261020.md. Older browser-only save controls remain convenience backups, separate from database records. Restart the old server before running this version.\n'
        payloads['README_FINANCIAL_DASHBOARD.md']=payloads['README.md']
    if args.dev_project_release:
        payloads['README.md']+=b'\n\n## Normal VS Code development project\n\nOpen this folder in VS Code. Read README_VSCODE_DEV.md. Run npm install, create the Python .venv and install backend/requirements.txt, then npm run dev. React/Vite serves port 5173 and the Python API serves port 8765. Separate frontend/ and backend/ entry folders are included. Shared checksum-verified engine/models remain at their existing paths. No personal database or virtualenv is shipped.\n'
        payloads['README_FINANCIAL_DASHBOARD.md']=payloads['README.md']
    if args.ui_refresh_release:
        payloads['README.md']+=b'\n\n## UI refresh - 21 October 2026 (current navigation)\n\nSeven focused pages replace the three crowded pages: Financial planner, Saved events, Booking calendar, What-If comparison, Reports & explainability, Price outlook, and Model evidence. Backend save/load/update/delete and browser backups now live on Saved events, not Financial planner. Calendar booking is separate. Health and reports are on Reports; model diagnostics and SHAP are on Model evidence. Financial rules, datasets, model weights and API contracts are unchanged. Read reports/UI_REFRESH_20261021.md. Your personal database is not shipped; do not overwrite or delete your existing runtime folder when upgrading. Earlier release notes above describe historical navigation and storage.\n'
        payloads['README_FINANCIAL_DASHBOARD.md']=payloads['README.md']
    if args.pp1_submission_release:
        payloads['README.md']+=b'\n\n## Final PP1 submission package - 21 October 2026\n\nThis package adds the complete technical dossier, dataset provenance/evidence files, current searchable Saved events UI, frozen model evidence, literature review and research gap documents. Start with reports/PP1_COMPONENT_COMPLETE_DOSSIER_20261021.md. It states exactly what was trained, how the synthetic dataset was constructed, the evaluation results and the scientific limitations. No personal SQLite database, real client data, node_modules, virtual environment or local LLM weights are shipped.\n'
        payloads['README_FINANCIAL_DASHBOARD.md']=payloads['README.md']
    manifest={'package':'PlanoVision Component 4 VS Code portable','version':'3.9-pp1-submission-20261021' if args.pp1_submission_release else '3.8-ui-refresh-20261021' if args.ui_refresh_release else '3.7-data-quality-20261021' if args.data_quality_release else '3.6-crud-connected-20261020' if args.crud_flow_release else '3.5-vscode-dev-20261020' if args.dev_project_release else '3.4-backend-crud-20261020' if args.backend_crud_release else '3.3-pp1-final-20261020' if args.pp1_final_release else '3.2-lkrgraph-localai-20261019' if ai else '3.1-component2bridge-20261018' if bridge else '3.1-gapclosure-20261018' if args.gap_closure_release else '3.1-portable-20261016',
        'created_utc':datetime.now(timezone.utc).isoformat(),'model_run':'expense_risk_v3_1_20261016',
        'scope':'LKR dashboard with native XGBoost/TreeSHAP, new LKR GAT comparator and local-only AI draft path; not full historical archive' if ai else 'Current LKR financial dashboard, native XGBoost/TreeSHAP, source and required evidence/artifacts; not full historical archive',
        'excluded':['virtual_environment','node_modules','large_v1_hybrid_release_archives','all_raw_downloads','legacy_Prophet_GAT_runtimes'],
        'scientific_status':'synthetic research only; stress limitations included; zero observed event outcomes',
        'files':{k:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for k,v in payloads.items()},
        'manifest_self_hash_excluded':True}
    payloads['PACKAGE_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
    prefix='PlanoVision_Component4/'
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,data in payloads.items():archive.writestr(prefix+name,data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:raise ValueError('zip_crc_failure')
        for name,data in payloads.items():
            if archive.read(prefix+name)!=data:raise ValueError('zip_payload_mismatch:'+name)
        work=ROOT/'work';work.mkdir(exist_ok=True)
        extract=Path(tempfile.mkdtemp(prefix='portable_zip_validation_',dir=work)).resolve()
        assert extract.is_relative_to(work.resolve())
        for info in archive.infolist():
            target=(extract/info.filename).resolve()
            if not target.is_relative_to(extract):raise ValueError('unsafe_zip_path')
        archive.extractall(extract)
    project=extract/'PlanoVision_Component4'
    check=subprocess.run([sys.executable,str(project/'scripts/research_pipeline/verify_portable_package.py')],cwd=project,capture_output=True,text=True,timeout=120)
    if check.returncode:raise RuntimeError('extracted_copy_smoke_failed:\n'+check.stdout+check.stderr)
    smoke=json.loads(check.stdout)
    if Path(smoke['root']).resolve()!=project.resolve():raise ValueError('smoke_used_original_checkout')
    assert all(sha256(ROOT/k)==v for k,v in protected.items()),'source_changed_during_packaging'
    digest=sha256(destination)
    destination.with_suffix('.zip.sha256').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    result={'status':'PASS_ZIP_AND_EXTRACTED_INFERENCE','archive':str(destination),'sha256':digest,
        'zip_bytes':destination.stat().st_size,'archive_entries':len(payloads),'extracted_test_root':str(project),
        'extracted_smoke':smoke,'source_files_unchanged':len(protected),
        'fresh_pip_install_tested':False,'note':'Smoke uses existing verified Python runtime on extracted independent source/artifact tree; no machine venv is shipped.'}
    report=ROOT/f'reports/portable_package_v3_1_20261016{suffix}.json'
    report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
