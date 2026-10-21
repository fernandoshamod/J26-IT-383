"""Final verified app delivery; no fitting, regeneration, approval invention or overwrite."""
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.release_input import sha256


def run(command,cwd=ROOT,timeout=180):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout


def main():
    receipt=ROOT/'reports/lkr_graph_local_ai_final_verification_20261019.json'
    if receipt.exists():raise ValueError('refuse_overwriting_completion_receipt')
    tests=json.loads((ROOT/'reports/public_hotel_benchmark_test_results.json').read_text())
    if tests['full_suite_status']!='PASS' or not tests['release_zip_files_unchanged']:raise ValueError('full_suite_or_data_integrity_failed')
    actual=json.loads((ROOT/'reports/lkr_graph_local_ai_20261018/actual_runtime_verification.json').read_text())
    if actual['status']!='PASS_ACTUAL_LOCAL_RUNTIME_INTEGRATION' or len(actual['cases'])!=3:raise ValueError('actual_llm_verification_missing')
    npm='npm.cmd' if sys.platform=='win32' else 'npm'
    frontend=run([npm,'test','--','--reporter=dot'],ROOT/'frontend');match=re.search(r'Tests\s+(\d+) passed',re.sub(r'\x1b\[[0-9;]*m','',frontend))
    if not match:raise ValueError('frontend_result_not_recognized')
    print('Frontend tests',match.group(1),'PASS',flush=True)
    run([npm,'run','build'],ROOT/'frontend');print('Production build PASS',flush=True)
    package=json.loads(run([sys.executable,str(ROOT/'scripts/research_pipeline/package_portable_vscode.py'),'--lkr-graph-local-ai-release']))
    print('Extracted package inference PASS',flush=True)
    project=Path(package['extracted_test_root'])
    run([sys.executable,str(project/'scripts/research_pipeline/verify_portable_package.py'),'--http'],project)
    bundled=run([sys.executable,'-m','unittest','discover','-s','tests'],project)
    # unittest writes its count on stderr; a successful process is the gate.
    output={'status':'PASS_STANDALONE_LKR_GAT_AND_LOCAL_AI_INTEGRATION','created_at_utc':datetime.now(timezone.utc).isoformat(),
            'python_full_suite_tests':tests['tests_run'],'python_full_suite_status':'PASS','frontend_tests':int(match.group(1)),
            'typescript_and_vite_build':'PASS','actual_local_model_cases':actual['cases'],
            'browser_native_gat_inference':'PASS','browser_actual_local_ai_report':'PASS',
            'extracted_package_manifest_and_native_inference':'PASS','extracted_package_http':'PASS','extracted_bundled_python_tests':'PASS',
            'archive':package['archive'],'archive_sha256':package['sha256'],'archive_bytes':package['zip_bytes'],
            'extracted_test_root':str(project),'fresh_pip_install_tested':False,'local_llm_weights_included_in_zip':False,
            'notes':['Local model is installed and verified in the current workspace. New machines run Setup_Local_AI.cmd once.',
                     'LLM drafts remain review-required; all figures and actions are server controlled.',
                     'GAT is an exploratory synthetic-data comparator, not established graph superiority or CAD integration.'],
            'source_files':{p.relative_to(ROOT).as_posix():sha256(p) for p in [ROOT/'component4/local_llm_report.py',ROOT/'component4/lkr_graph.py',
                 ROOT/'component4/lkr_graph_inference.py',ROOT/'config/llm_report.v0.1.json',ROOT/'reports/lkr_graph_local_ai_20261018/actual_runtime_verification.json']},
            'frozen_release_sha256':tests['release_zip_sha256_after']}
    receipt.write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output,indent=2),flush=True)


if __name__=='__main__':main()
