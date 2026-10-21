"""Rerun old + new tests and report exact gates; never run a pilot or bulk generator."""
import hashlib
import json
from pathlib import Path
import platform
import unittest

import numpy as np
from component4.engine import fingerprint
from component4.generator_validation import CODE_FILES, file_snapshots
from component4.scenario_generator import pilot_execution_blockers

ROOT = Path(__file__).resolve().parents[2]


def flatten(suite):
    for case in suite:
        if isinstance(case,unittest.TestSuite):
            yield from flatten(case)
        else:
            yield case.id()


def main():
    suite = unittest.TestLoader().discover(str(ROOT/'tests'))
    ids = list(flatten(suite))
    old = [x for x in ids if not x.startswith('test_scenario_generator.')]
    new = [x for x in ids if x.startswith('test_scenario_generator.')]
    assert len(old)==45, 'An existing test was added/removed; review suite inventory'
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    candidate = json.loads((ROOT/'config/simulator.candidate.json').read_text(encoding='utf-8'))
    gates = pilot_execution_blockers(candidate)
    previous_manifest = json.loads((ROOT/'reports/configuration_hash_manifest.json').read_text(encoding='utf-8'))
    preserved = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in previous_manifest['input_file_sha256'].items()}
    for p,sha in previous_manifest['deliverable_file_sha256'].items():
        preserved[p] = hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha
    assert all(preserved.values()), 'Historical Stage 1/2 inputs or deliverables changed'
    report = {
        'audit_date':'2026-10-11','status':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'existing_tests':len(old),'new_generator_tests':len(new),
        'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'python':platform.python_version(),'numpy':np.__version__,
        'seed_used_only_in_software_fixture':314159,'actual_approved_seed':candidate.get('seed'),
        'code_sha256':file_snapshots(ROOT,CODE_FILES+('tests/test_scenario_generator.py','fixtures/scenario_generator_test_fixture.py')),
        'candidate_sha256':fingerprint(candidate),'historical_files_preserved':preserved,
        'exact_pilot_blockers':gates,'test_ids':ids,
        'pilot_generated':False,'bulk_dataset_generated':False,'models_trained':False,
        'scope':'1–16 mock records per in-memory unit-test call; two-record serializer checks in removed temporary directories. No observed rates/outcomes or project scenario dataset.'
    }
    (ROOT/'work/generator_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    text = f'''# Stage 3 generator test results

Audit date: 11 October 2026. Status: **{report['status'].upper()}**.

## Executed tests

- Original tests preserved: {len(old)}.
- New generator tests: {len(new)}.
- Total executed: {result.testsRun}; failures: {len(result.failures)}; errors: {len(result.errors)}; skipped: {len(result.skipped)}.
- Runtime: Python {platform.python_version()}, NumPy {np.__version__}. Fixture seed: 314159, test-only; approved production seed remains null.
- Scope: reconciliation, inclusive/exclusive tax, zero bundled charges, geometry/capacity/AV scope, physical versus billed paid hours, reserve/profit, retained risky cases, strict missing/type/unit/date/domain checks, same-seed replay, stable prefix/IDs, source/code hashes, ancestry, simulated labels, shock/injection separation, whitelist leakage boundary and rejection before output creation.

Initial test execution encountered Windows sandbox system-temporary-directory permissions. Re-execution with permission passed; the tests now use scoped temporary directories inside the writable project `work` folder and verify their resolved location before cleanup. This was an environment/file-access issue, not an accounting failure. The reproducible final run above is the acceptance record. The original financial engine/gates and Stage 1/2 inputs remain unchanged from their historical snapshots.

Tests used only small software fixtures (1–16 records per call), with explicit mock origin. The serializer test used two records in an automatically removed temporary directory. One approval-shape/hash test constructs an explicitly fake in-memory UNIT TEST record for branch coverage; it is never written as a project approval and still cannot authorize the fixture in live mode. The test report contains no scenario financial records. No pilot, bulk dataset or trained models were created.

## Current approval status

The current candidate is **proposed, incomplete and not frozen**. All 108 active numerical values remain null. No Stage 2 reviewer records were populated and no policy option was selected. {sum(preserved.values())} historical input/deliverable snapshot checks passed. The implementation now exists, but tests do not confer accepted generator verification or domain approval. Source/evidence/model limitations in `generator_design.md` still apply.

Exactly {len(gates)} distinct blocker codes were returned by `pilot_execution_blockers(config/simulator.candidate.json)`. A parser is fail-fast, so `scenario_generator:object_required` represents the missing complete generator specification; it is not evidence that its nested seed/weights/date/domain/code/version requirements are satisfied. Those must all be specified and reviewed when the spec is supplied.

Outstanding requirements are:

1. Genuine approvals for all 19 active engine formulas and the new sampling/outcome/anomaly design, with actual reviewer/role/date/version/rationale/evidence records. Technical recommendations and test flags are insufficient.
2. Both complete approved numerical/rate/tax/bundle/geometry/staffing profiles and approved override bounds. Obtain compatible dated Sri Lankan quotations and measured plans; do not promote mock rates or source advertisements automatically.
3. Explicit choice of generator seed, maximum attempts, archetype weights, date/input domains, budget and retained-receipt policies, bounded shock/dependence/service scope and anomaly regime. The stochastic uniform mechanism is a capability, not an approved distribution or calibrated prevalence.
4. Matching real source-file and code hashes, calibration cutoff, ancestry and exact Python/NumPy runtime spec; genuine measured geometry and fully seated scope or a separately reviewed engine amendment.
5. A fully specified freeze and genuine `generator_approval` payload hash/version record, then independently accepted generator implementation/test/sampling/provenance documentation. Do not set the verification flag automatically because these tests pass.
6. Explicit user/supervisor authorization for exactly 20–50 diagnostic records, approved whole-scope pilot hash and all five existing evidence references. Material edits invalidate the former scope/hash. Bulk generation/training remain a separate future decision.

### Exact machine-readable blocker list

```text
''' + '\n'.join(gates) + '''
```

## Reproduce without generating a dataset

```powershell
Set-Location 'C:\\Users\\User\\Documents\\ChatGPT\\ML'
$env:PYTHONPATH = (Get-Location).Path
python -m unittest discover -s tests -v
python scripts/research_pipeline/test_generator.py
```

The second command refreshes this report and `work/generator_verification.json`, not approval records or scenario datasets. Exact test IDs, code identities and candidate fingerprint are retained in that JSON audit. A passing suite is software validation only, not real-world predictive validity.
'''
    (ROOT/'reports/generator_test_results.md').write_text(text,encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','tests_run','existing_tests','new_generator_tests','failures','errors','pilot_generated']},indent=2))
    print('Distinct current pilot blockers:',len(gates))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__=='__main__':
    main()
