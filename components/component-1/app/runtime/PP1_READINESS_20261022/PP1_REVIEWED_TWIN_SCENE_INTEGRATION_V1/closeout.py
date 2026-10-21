import json,hashlib,ast,re,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,v):
 with (H/name).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2)
prior=H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'
previous=read(prior/'CONTROLLED_001/A_INITIAL/RESULT.json')['qualification_fingerprint']['code']
assert all(sha(ROOT/p)==value for p,value in previous.items())
models=read(prior/'FUNCTIONAL_ACCEPTANCE_FINAL.json')['models']
assert all(sha(row['path'])==row['sha256'] for row in models.values())
report=read(H/'PATH_A/ANALYSIS.json')['model_report']
original=report['original_document'];assert sha(original['path'])==original['sha256']
http=read(H/'HTTP/GUARD_EVENTS.json');guard=read(H/'CONTROLLED_003/GUARD_EVENTS.json')
assert not http['network'] and not http['denied_writes']
assert not guard['network_attempts'] and not guard['denied_writes']
for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for p in H.glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if not target.startswith(('http:','https:','#')):assert (p.parent/target).is_file(),(p,target)
save('FINAL_PACKAGE_CHECKS.json',dict(status='PASS',python_syntax=True,local_markdown_links=True,models=models,unchanged_prior_scene_compiler_policy_optimizer_hashes=previous,actual_source_hash=original,python_external_network_attempts=0,denied_writes=0,complete_os_isolation_claimed=False,frontend_browser='NOT_EXECUTED',genuine_venue='NOT_EXECUTED'))
save('EXECUTION_BINDING_DETAILS.json',dict(original_worker=str(H.parent/'PP1_FINAL_DEMO_REHEARSAL_V1/worker.py'),original_worker_sha256=sha(H.parent/'PP1_FINAL_DEMO_REHEARSAL_V1/worker.py'),in_memory_insertions=['adapter.install(runtime, OUT) before original repair/scenarios imports','SQLite audit exception for explicit file:...?mode=ro registered database reads'],algorithm_edits=0,source_file_edits=0,scope='Controlled registered HTTP Twin inlet replaces prior synthetic Scene constructor; original search/verification code executes',authority='Explicit simulated fixture, not genuine human consent'))
print('Syntax, links, model/source hashes, prior compiler/policy/optimizer and guards PASS')
