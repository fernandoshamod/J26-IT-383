"""Consolidate review evidence and write decision documents; no scenario generation or approvals."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from component4.engine import FORMULA_IDS, evaluate
from component4.scenario_generator import pilot_execution_blockers
from component4.unitless_experiment import validate_unitless_config, unitless_pilot_blockers

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'dataset-recovery.0.2-proposed'


def read(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))


def write(p, text):
    (ROOT / p).write_text(text, encoding='utf-8')


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    tables = read('work/minimal_pilot_review_tables.json')
    lkr = read('config/minimal_pilot_candidate.json')
    unitless = read('config/unitless_pilot.proposed.json')
    assert {f['assumption_id'] for f in tables['formulas']} == set(FORMULA_IDS)
    assert len(tables['numerical']) == 108
    assert validate_unitless_config(unitless)
    stage_reports = {}
    for path in sorted((ROOT / 'reports').glob('*.md')):
        text = path.read_text(encoding='utf-8-sig')
        stage_reports[path.relative_to(ROOT).as_posix()] = {'sha256': sha(path.relative_to(ROOT)), 'characters_read': len(text)}
    blockers = []

    def add(bid, category, source, severity, stages, cause, action, owner, status, verify):
        blockers.append({'Blocker_ID': bid, 'Category': category, 'Original_Report_or_File': source,
                         'Severity': severity, 'Affected_Stage': stages, 'Root_Cause': cause,
                         'Exact_Required_Action': action, 'Responsible_Decision_Maker': owner,
                         'Status': status, 'Verification_Condition': verify,
                         'Reviewer': None, 'Review_Date': None, 'Decision_Reference': None})

    items = [
        ('E01','Missing evidence','reports/parameter_evidence_summary.md','Critical','5–7','Advertisements lack full compatible date/tax/package terms; 28 proposed-active financial nulls remain','Obtain seven compatible rate/tax cards per profile OR explicitly choose separate dimensionless experiment','User + providers + accounting/domain reviewer','Open','Every active card has rates, units, dates, inclusions/taxes, hashed evidence and genuine review'),
        ('E02','Missing evidence','reports/missing_real_world_data_checklist.md','High','6; later modeling','No independent observed event-financial outcomes or labels','Collect consented observed records; until then disclose external validation NOT PERFORMED','User + supervisor','Open','Independent held-out observed records or explicit simulator-only methodological disposition'),
        ('E03','Missing evidence','config/minimal_pilot_candidate.json','Critical','5','Hypothetical rectangle is not measured venue geometry','Choose measured evidence for LKR branch or review truthful separate hypothetical protocol','Supervisor + venue practitioner','Open','Approved geometry-origin contract; no relabelling invented layout as measured'),
        ('A01','Missing approval','reports/pilot_authorization_conditions.md','Critical','5','No exact-hash/count pilot authority','Complete prerequisites, freeze payload and obtain genuine 20–50-row authorization','User/supervisor with legitimate authority','Open','Real approval record binds frozen version/hash/count/scope; existing gates zero blockers'),
        ('A02','Missing approval','reports/pilot_acceptance_criteria.md','Critical','5–6','AC01–AC14 unaccepted and old 40-root/LKR criteria incompatible with proposed 24-row unitless design','Approve branch-specific pre-results arithmetic, coverage and rejection criteria','Supervisor + experiment designer','Open','Versioned criteria accepted before results; no retrospective goalpost change'),
        ('A03','Missing approval','reports/pilot_readiness_report.md','Critical','5','Numeric, generator and implementation verification records pending','Review complete branch-specific payload and independently accept software verification','Supervisor/domain reviewer + user','Open','Actual reviewer/role/date/rationale/evidence and exact scope hash; no automatic workbook import'),
        ('A04','Missing approval','reports/configuration_hash_manifest.json','Critical','5–7','No approved frozen configuration/code/source/runtime identity','Freeze only the completed reviewed branch; include new modules in future code snapshot manifest','Reviewer + project maintainer','Open','All frozen byte/payload hashes recomputed and matched immediately before execution'),
        ('D01','Design flaw','reports/final_sampling_strategy.md','Critical for unseen venues','7; later evaluation','Both archetypes share HYP-VENUE-432M2-v1; transitive source grouping gives one group','Keep IDs truthful; select conditional in-simulator protocol OR collect genuine independent templates','Supervisor + designer','Open','Protocol explicitly accepted; no fabricated source diversity'),
        ('D02','Unsupported experiment','reports/final_sampling_strategy.md','High','later evaluation','Current source pool cannot hold out unseen venue/vendor distributions','Mark unseen-venue evaluation unsupported; do not report its accuracy','Supervisor','Unsupported','No unseen-venue claim; future independent source profiles reviewed before reopening'),
        ('D03','Design flaw','reports/final_dataset_generation_plan.md','High','7','7500 related rows are not 7500 independent samples','Report 1250 conditional roots, 3750 planning states and 7500 outcomes separately','Designer + supervisor','Open','Ancestry preserved, effective source size disclosed and group-level evaluation used'),
        ('D04','Design flaw','reports/minimal_pilot_scope.md','High','5','Older scope says independent per-service cost factors, but code uses one common factor','Adopt accurate shared-cost wording or approve a separately versioned dependence change','Supervisor + designer','Open','One consistent reviewed dependence definition across config, prose and generator'),
        ('D05','Design flaw','reports/financial_dependency_rules.md','High','5','Legacy ceil-area AV rule differs from implemented independent threshold steps','Review A011 and reconcile register/rules/code to one version','AV/domain reviewer + supervisor','Open','Threshold boundaries and kit scope agree; amended formula records genuine'),
        ('D06','Design flaw','reports/final_sampling_strategy.md','High','7','Guest ±1 intervention changes root support and repeated outcomes need reviewed pairing','Review interior support, without-replacement roots, duplicates and common-random-number replications','Designer + supervisor','Open','New sampling version accepted before diagnostics; no label-driven rejection'),
        ('S01','Software defect','component4/scenario_generator.py','High','7','Tuple-only grouping misses partial and transitive source overlaps','Use tested connected components with underlying source dependencies in future integrated writer','Maintainer + methodology reviewer','Resolved software only','New split_components tests cover shared venue, vendor, source and transitive chains; integration still S05'),
        ('S02','Software gap','reports/final_sampling_strategy.md','High','7','No machine-readable independent leakage audit','Run read-only audit on future metadata and assignment map; do not claim current dataset PASS','Maintainer','Resolved software only','CLI and tests reject split families, duplicate plans, missing metadata, unknown maps and empty partitions'),
        ('S03','Software gap','config/bulk_generation_candidate.json','High','7','Count/quota validation for root × state × replication was missing','Use strict expansion validator and additional fail-closed bulk preflight checks','Maintainer','Resolved software only','Count/unit/type/quota and missing-authority tests pass; no bulk writer permission inferred'),
        ('S04','Software gap','reports/remaining_approval_blockers.md','High','5','Existing LKR engine cannot represent explicit exclusions or honest unitless scores','Separate dimensionless config/validator/test calculator; do not populate LKR fields','Maintainer + supervisor','Resolved software only','Unitless test path rejects LKR/origin mixing, reconciles scores and records seven disabled services'),
        ('S05','Software gap','component4/scenario_generator.py','Critical','5 for expanded diagnostic;7','Existing stochastic generator has no exact quotas, variants, paired replications or bulk writer','Implement reviewed expanded design with stable IDs/RNG streams and separate authorization gates','Maintainer after protocol selection','Open','Tests plus independently accepted 20–50-row diagnostics cover actual integrated path; pilot cap preserved'),
        ('S06','Software gap','component4/unitless_experiment.py','Critical for unitless branch','5','Unitless stochastic outcomes and authorized persistence are not implemented','Implement separate unitless RNG/outcome/label/ledger writer after methodological scope selection','Maintainer + supervisor','Open','Versioned branch tested; score fields only; approvals/hash/source gates verified; no LKR fallback'),
        ('S07','Software gap','component4/engine.py','Critical for restricted LKR branch','5','28 proposed excluded slots remain required; zero effective disables in original engine','Either complete all original cards or implement reviewed explicit excluded-service ledger semantics','Maintainer + accounting reviewer','Open','No false bundle/zero quotation; all 14 ledger identities accounted for and existing tests preserved'),
        ('S08','Software gap','component4/generator_validation.py','Critical for hypothetical LKR branch','5','Original live parser requires measured_reviewed_plan','Keep LKR blocked; choose measured data or review and implement explicitly separate hypothetical geometry mode','Maintainer + supervisor','Open','Truthful mode/provenance plus physical checks; not falsely measured'),
        ('V01','Missing validation','reports/pilot_execution_report.md','Critical','5–6','No diagnostic execution or rows exist','Execute only after genuine exact-hash branch authorization','User + maintainer','Open','All required pilot artifacts plus replay/rejection logs from authorized run'),
        ('V02','Missing validation','reports/pilot_final_assessment.md','Critical','6–7','Stage 6 FAIL due to missing pilot, not tested bad economics','Run distributions, dependency, sensitivity, label and replay assessment against preaccepted criteria','Supervisor + analyst','Open','Actual independent assessment PASS/disposition; no inference from unit tests'),
        ('A05','Missing approval','reports/bulk_generation_authorization.md','Critical','7','Separate exact-count frozen-hash bulk authority absent','Request only after approved diagnostics and implementation; count 7500 remains proposal','User/supervisor','Open','Real bulk-only approval binds configuration, code, sources, scope/count and split policy'),
        ('D07','Design flaw','reports/numerical_parameter_review.md','High','5','Accounting boundary, compound tax, bundles, paid staffing and retained receipt scope unreviewed','Select coherent restricted boundary; review inclusion/rental-period and revenue semantics','Accounting/domain reviewer + supervisor','Open','Selected compatible cards and formula reviews show no double charging'),
        ('A06','Missing approval','config/unitless_pilot.proposed.json','Critical for unitless branch','5','Complete hypothetical values are not approved choices','Review all score coefficients/references, geometry, domains, shocks and 24-row scope','Designer + methodology supervisor','Open','Signed/referenced review covers exact unitless payload; original LKR approvals not reused')
    ]
    for x in items:
        add('C4-' + x[0], *x[1:])
    for f in tables['formulas']:
        add('C4-F-' + f['assumption_id'], 'Missing approval', 'reports/formula_review_decisions.xlsx; component4/engine.py', 'Critical', '5–7',
            f['assumption_id'] + ' formal decision pending', f['recommendation'] + ' recommendation: ' + f['recommendation_rationale'],
            'Supervisor + relevant domain reviewer', 'Open', 'Actual reviewer/role/date/rationale/reference binds formula version; recommendation is not approval')
    for n in tables['numerical']:
        cause = n['classification'] + '; ' + n['scope']
        if n['proposed_value'] is None:
            cause += '; value remains null'
        add('C4-P-' + n['decision_id'], 'Missing evidence' if n['proposed_value'] is None and not n['classification'].startswith('4.') else 'Missing approval',
            'config/minimal_pilot_candidate.json: ' + n['path'], 'Critical' if n['scope'] == 'Active proposal' else 'High', '5–7 LKR branch',
            cause, n['rationale'], 'User + supervisor; provider/accounting reviewer for rate/tax evidence', 'Open',
            'Compatible non-null approved active value OR genuinely implemented approved exclusion; unitless branch requires separate mapping')

    classification = Counter(n['classification'] for n in tables['numerical'])
    review = ['# Formula and parameter decisions — consolidated recovery', '', f'Version `{VERSION}`; 11 October 2026. Advisory only. All 19 formal formula decisions and all 108 original numerical review decisions remain pending.', '',
              '## Formula-by-formula recommendations', '',
              'Recommendations apply to the restricted provisional LKR model. Unitless treatment requires its own versioned methodology review: tax/rate identities do not become market evidence by removing currency. No current relationship is empirically fitted to event-level outcomes.', '']
    for f in tables['formulas']:
        review += [f"### {f['assumption_id']} — {f['title']}: {f['recommendation']}", '',
                   f"Actual definition: `{f['actual_formula']}`.", '', f"Purpose: {f['purpose']}", '',
                   f"Inputs: {f['required_inputs']}", '', f"Evidence references: {f['supporting_refs']}. These are document/advertisement references, not fitted event relationships.", '',
                   f"Recommendation: {f['recommendation_rationale']}", '', f"Limitations: {f['limitations']}", '',
                   'Formal decision: **Pending**, reviewer/date/rationale/approval reference blank. Supervisor and relevant domain reviewer decide.', '']
    review += ['## All 108 original numerical slots', '',
               'Published amounts are evidence leads, not fully scoped approved prices. Unknown rates/taxes remain null. Existing source facts and dates are preserved; public pages were not newly inspected or represented as current quotations in this recovery.', '',
               'Classification totals: ' + '; '.join(f'{k}: {v}' for k, v in classification.items()) + '.', '',
               'There are 52 specified non-price proposals, 28 unresolved proposed-active rate/tax fields and 28 proposed excluded fields. The unchanged LKR engine still requires all 56 financial nulls and implements zero exclusions. **No field is currently both formally approved and explicitly disabled in that engine.**', '',
               '| Profile | Exact parameter/path | Category | Proposed value | Unit | Evidence / required action |',
               '| --- | --- | --- | --- | --- | --- |']
    for n in tables['numerical']:
        review.append('| ' + ' | '.join(str(x).replace('|', '/') for x in (n['event_type'], n['path'], n['classification'], 'null' if n['proposed_value'] is None else n['proposed_value'], n['unit'], n['evidence_refs'] + ': ' + n['rationale'])) + ' |')
    review += ['', '## Separate unitless proposal — not an LKR fallback', '',
               '`config/unitless_pilot.proposed.json` uses a dimensionless cost index, not LKR, USD or converted public prices. Each score line is `alpha_service × quantity/reference_quantity`. Reference quantities are invented experimental scaling constants: 100 guests/chairs, 17 tables, 12 m2 stage, one AV kit, 36 billing person-hours and one booking. Coefficients catering/chairs/tables/stage/AV/labour/venue = 1/.1/.2/.3/.2/.4/.5 are arbitrary design choices, not relative market price estimates. They are not normalized observed quotations.', '',
               'Budget and retained receipt score choices [2,3,4] are independent hypothetical funding/receipt settings. Reserve .10 and required margin 10 points are hypothetical policies. No FX/rate conversion factor exists. Sum scores once; reserve is separate funding; profit score is receipts minus expense score. Zero receipts means unavailable margin. Tax is **not modeled**, not asserted zero VAT. Deposits/pass-throughs are outside this restricted experiment.', '',
               'The seven active components have complete proposal coefficients/reference quantities. Seven omitted services are explicitly absent from this standalone score ledger; this is implemented only in the isolated test calculator, not the original LKR engine. The 24×18 m venue, 400 m2 usable area, 1.5 m2 seat zone, circulation/service areas, staffing and AV steps remain hypothetical; no measured layout/safety claim.', '',
               'Proposed ordinary cost factor [0.9,1.1] is common across active services; receipt factor independent [0.9,1.1]. Injection .10, severity [1.25,1.5], one positive stage/AV/labour line, remains an uncalibrated experimental design; no unitless stochastic generator is implemented. Planning features must precede these latents. Scores and score outcomes must NEVER populate currency-valued 46-column master fields; use separate unitless tables/schema.', '',
               'User/designer selects experiment scope, coefficients, domains, quotas, seed, policies and pairing. Supervisor accepts methodological/formula/label/evaluation limitations and changed criteria. Provider/accounting review remains mandatory for any LKR branch. Complete proposal values are not approvals; original review records cannot authorize a new unitless branch.']
    write('reports/formula_and_parameter_decisions.md', '\n'.join(review) + '\n')

    write('reports/sampling_ancestry_review.md', '''# Sampling ancestry review

Version dataset-recovery.0.2-proposed; 11 October 2026. No financial scenarios generated.

| Term | Exact definition and independence boundary |
| --- | --- |
| Synthetic root configuration | One addressed planning draw conditional on fixed simulator/templates and domains, before interventions or outcomes. Distinct draw/ID is not an independent real event. Without-replacement deduplication further prevents an IID claim. |
| Planning intervention | Controlled pre-outcome change to a root, such as guest count minus/plus one. Recompute dependent resources/costs; freeze budget/receipts and other exogenous drivers. Child states are not independent roots. |
| Outcome replication | New addressed bounded realization draw conditional on the same planning state. Common random numbers across variants deliberately couple comparisons; no replication is an observed event. |
| Venue template ancestry | Actual identity of the measured or hypothetical geometry/arrangement and its derivation. Copies/renamings do not create new venues. |
| Vendor template ancestry | Identity of the exact scoped coefficient/rate-card design plus underlying provider/quotation ancestry. Different aggregate cards sharing restricted quotes are related. |
| Source ancestry | Exact snapshot hashes plus identifiers of actual shared quotation/calibration dependencies. Global software/rules identify the experiment, not new independent sources. |
| Scenario family ID | Stable identity of root planning scope/index/accepted attempt; all its states and outcomes retain this family. It is metadata, never a predictor. |
| Split group ID | Stable hash of transitive related-family membership under the declared protocol; not simply the full venue/vendor tuple. |

The 1250 × 3 × 2 architecture means 1250 conditional root draws, 3750 planning states and 7500 realization rows, not 7500 independent samples. Equal 625-root archetype quotas are experimental coverage, not Sri Lankan frequencies. Stage 7 remains an unapproved proposed design.

Both current LKR profiles use HYP-VENUE-432M2-v1, an invented 24×18 m rectangle. Wedding/Corporate cards are unresolved. The unitless proposal honestly reuses the same venue identity and uses one hypothetical coefficient card. Under unseen-template grouping the source pool collapses to one component; unseen-venue/vendor evaluation is unsupported. Do not fabricate layout observations, quote provenance or new IDs to pass splitting.

New utility code implements connected components and an independent leakage audit but does not change the original stochastic generator's tuple-based metadata or live gates. Those historical source/code hashes still identify their original files. Future integration must version the expanded generator, add all new dependency modules to frozen code hashes and invalidate/review affected approvals. None currently exist to reuse.

For a 24-row diagnostic propose four roots (two each), three states and two paired outcomes; this is a new pending scope, not the old 40-root approval. Four families cannot supply a meaningful 70/15/15 model evaluation. Use that pilot for arithmetic/dependency/replay diagnostics only, no modeling or accuracy claims.
''')
    write('reports/group_split_strategy.md', '''# Grouped split strategy — conditional in-simulator proposal

Version dataset-recovery.0.2-proposed. **Protocol change requires supervisor acceptance.** The Stage 7 strict-source split remains impossible with the current source pool; this document offers a separate narrower evaluation question, not a silent waiver.

## Two protocols

`conditional_in_simulator`: assess recovery of synthetic rules within the fixed hypothetical geometry/vendor design. Join all descendants of each family and merge different families sharing identical planning fingerprints. Never split these connected groups. Shared venue/vendor/source metadata across partitions are expected and explicitly disclosed, not hidden. This protocol supports no unseen-source, Sri Lankan market, temporal forecasting or real-event generalization claim. Keep those identities as audit metadata, not predictors.

`unseen_templates`: additionally join families sharing venue, vendor or underlying source dependency identifiers transitively. Current one shared venue yields one component, so a three-way split is blocked. New IDs or alternative random dimensions inside the same unvalidated template are not genuine empirical diversity.

## Deterministic assignment

Build metadata and groups after planning but before realized outcomes. Stable group ID hashes sorted family membership and protocol. Target 70/15/15 row fractions; sort largest component first, tie-break with SHA256 UTF-8 `bulk-split-v0.1|seed|group_id`. Assign first three groups train/validation/test, remaining groups to greatest target row deficit (tie order train/validation/test). Require at least three groups, all partitions nonempty, and ±5 percentage-point tolerance; fail rather than divide a related group. Proposed split seed 20261023 is predeclared, not searched after labels. Root quotas apply overall, not automatically each split. Preserve event counts and achieved proportions in the split manifest.

The four-family diagnostic is not a training dataset; do not force it through these bulk fraction thresholds or claim reliable holdout performance. Existing Stage 7 strict-source assumptions must be explicitly amended if the narrower conditional question is selected. Model training remains separately unauthorized.

## Machine-readable validation

`component4/dataset_design.py` provides `split_components`, `assign_groups`, and independent `audit_split_leakage`. Supply JSON metadata rows with `scenario_id`, `family_id`, `planning_fingerprint`, `venue_template_id`, `vendor_template_id`, `source_dependency_ids`, plus a separate ID→split map. Actual source dependency aliases/renamed copies must be resolved upstream; the utility cannot authenticate a provider or detect fraudulent IDs.

Windows read-only check after an authorized run (substitute real file paths):

```powershell
$env:PYTHONPATH = 'C:\\Users\\User\\Documents\\ChatGPT\\ML'
& 'C:\\Users\\User\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' scripts/research_pipeline/audit_split_leakage.py --metadata '<metadata.json>' --assignments '<split-map.json>' --protocol conditional_in_simulator
```

JSON reports PASS/FAIL, prohibited overlaps, empty partitions and disclosed source overlaps; failed/malformed checks exit 1. A missing dataset is NOT PERFORMED, never a zero-leakage PASS. `reports/split_leakage_validation.json` records current absence and software test evidence only. Unit tests exercise shared sources, transitive chains, shared families, identical states, input-order invariance and broken maps.

Only pre-event allowlisted inputs enter later models. Outcomes, ledgers, injection flags, latent factors, IDs, seeds, groups and split membership are forbidden predictors. Fit preprocessing/tuning only on training groups; group-level evaluation recognizes root dependence. Exact duplicate planning states may strongly collapse groups; disclose achieved diversity instead of manufacturing new identities.
''')
    lkr_reasons = pilot_execution_blockers(lkr)
    unitless_reasons = unitless_pilot_blockers(unitless)
    write('reports/stage5_recovery_plan.md', f'''# Stage 5 recovery plan — two honest branches

Version {VERSION}; 11 October 2026. Stage 5 remains blocked; Stage 6 has no actual PASS. No execution authority is inferred from this request.

## LKR branch

All 19 formula records and 108 original numeric decisions remain pending. Restricted scope has 28 unresolved active financial values plus 28 proposed exclusions; unchanged engine requires 56 financial nulls. Current read-only checker returns {len(lkr_reasons)} distinct machine blockers (fail-fast, not an exhaustive nested certificate). Both live engine profiles remain blocked with null results.

Obtain compatible seven-component quotes per profile with exact units, dates, taxes and bundle scope; actual geometry/paid schedules or genuinely approved hypothetical scope; complete old 14-service cards or implement explicit exclusions. Approve formulas and numeric/outcome/sampling payloads, implement scope-compatible changes with tests, freeze all selected code/source/runtime versions, then obtain exact-hash/count authority. Do not use procurement totals, foreign prices or mock rates as retail cards.

## Recommended immediate alternative: dimensionless diagnostic

If compatible local evidence cannot be obtained in time, select the separate unitless experiment. Its coefficient, normalization-reference, domain, policy and bounded-shock proposal values are structurally specified, with currency null and no market conversion. That removes the **market-rate requirement only for the narrower experiment**. It does not supply market evidence or allow the normal LKR API to return scores.

1. Designer selects unitless scope/coefficients/reference quantities, truthful invented geometry, fully seated/no VIP restrictions, disabled-service boundary, policy values and proposed 24-row (4×3×2) diagnostic design.
2. Supervisor formally reviews revised score formulas, omission/tax treatment, pairing/shocks/injections, labels, conditional evaluation and limitations. Existing A001/A011/accounting reviews need branch-specific treatment; no LKR approval reused automatically.
3. Implement exact quotas, guest interventions, replication-aware IDs/RNG, dimensionless realization ledgers/labels, prediction-feature allowlist and separately gated unitless writer. Current code contains configuration validation and an isolated deterministic **test-only** calculator, not this stochastic execution path.
4. Run old/new tests and obtain independent accepted verification. Approve amended pre-results criteria: score reconciliation at an explicitly specified numerical tolerance (propose 1e-12 absolute score discrepancy), integer geometry/resource constraints, 24 rows/four roots/12 planning states, two roots per archetype, exact replay, complete provenance and legitimate loss retention. Reject invalid plans before outcomes; no label-balance target.
5. Freeze complete branch payload/source/code/runtime/criterion identities externally, then obtain genuine explicit 24-row scope/hash permission. Active authorized count is currently null and authority false. Only then generate; evaluate Stage 6 independently afterwards.

Proposed criterion differences are material: old LKR .01 rounding, measured geometry and 40-root diversity requirements cannot silently carry over to unitless scores/hypothetical venue/four roots. Exact replay is a stronger reproducibility criterion than a tolerance-based comparison. One common cost factor and independent receipts factor are accurate current design wording; arbitrary probabilities do not estimate market risk.

## Present technical disposition

- Fixed in new utilities: transitive ancestry grouping; independent leakage audit/CLI; strict expansion count/quota validation and additional bulk preflight; dimensionless proposal validation and isolated score arithmetic/exclusion checks.
- Original Python engine, API and diagnostic generator are unchanged; their pilot cap and mock/live separation remain intact. New utilities are not yet integrated into the production stochastic writer and cannot grant approvals.
- Not implemented: expanded stochastic generation/authorized persistence, particularly the unitless outcome path. These are explicit blockers, not hidden behind passing tests.
- Unitless pilot checker returns: {', '.join(unitless_reasons)}.

Minimum viable pilot can **not** proceed now. It need not be unitless if genuine LKR evidence is completed; absent that evidence, unitless is the honest recommended simulator-only alternative. Neither branch is ready for explicit execution authorization. Stop before rows/training; do not claim Stage 6 passed.
''')
    write('reports/pilot_approval_decision_packet.md', f'''# Next pilot decision packet — scope review, not execution authority

Version {VERSION}; 11 October 2026. **NOT READY FOR EXPLICIT STAGE 5 EXECUTION AUTHORIZATION.**

## Decide the experiment branch

Option A: continue LKR evidence collection and approve compatible rates, taxes, measured/reviewed scope and formula/numeric records. This permits later claims only within accepted evidence/limitations; public advertisements alone are insufficient.

Option B (recommended where rates cannot be supported): approve the methodology for a **dimensionless, hypothetical** Wedding/Corporate experiment. All score coefficients are arbitrary design choices, not real relative prices. No conversion to LKR exists. Proposed diagnostic scope is 24 rows = four roots (two each) × base/guest−1/guest+1 × two paired outcomes. This is not 24 independent events and not a model evaluation dataset.

Both choices currently require genuine records. Selecting a branch does NOT authorize generation. No reviewer name, signature, date or rationale is filled by software.

## User/designer decisions — pending

- Branch A or B and analytical service boundary; exclusions are not free services or provider bundles.
- Four-root/24-row or alternative 20–50 scope, exact archetype quotas, ±1 guest intervention, interior root bounds and paired replications.
- Hypothetical geometry, seating/staffing settings, score coefficients/reference quantities (B only), independent budgets/retained receipts, reserve/margin policies.
- Predeclared seed/attempt cap, common-cost/independent-receipt shocks, injected regime/service scope and no class-balance tuning.
- Conditional in-simulator evaluation as a separately revised future question; unseen-venue evaluation remains unsupported.

## Supervisor/domain decisions — pending

- All 19 formula decisions: 10 recommended Accept and 9 Modify; zero recommendations are formal approval. Domain review for real billing/taxes/arrangement/staffing; methodology-specific review for arbitrary unitless relationships.
- Geometry/omitted-service and accounting boundaries, non-overlapping ledger quantities, truthful score interpretation, labels and predictor leakage boundary.
- Amend AC01–AC14 before outcomes for selected currency/geometry/count scope; accept repeatability/dependency/sensitivity coverage and simulator-only realism limits.
- Accept tested integrated stochastic implementation and provenance, not just utility tests; choose source grouping taxonomy and forbid unseen-source claims on the current one-venue pool.

## Conditions before a later execution decision

Complete selected configuration/units/evidence → genuine formula/numerical/methodology review → reviewed stochastic/writer implementation → full tests and independently accepted verification → preaccepted branch-specific criteria → frozen simulator/code/source/runtime/seed/scope payload → explicit authorization tied to that exact hash and 20–50 count.

Approved configuration version: **null**. Frozen simulator hash: **null**. Authorized scenario count: **null**. Approved reviewer/date/rationale/evidence: **blank**. Explicit pilot authority: **false**. Stage 6 validation PASS: **false**. Draft proposal file hashes in `work/dataset_recovery_audit.json` identify bytes only, not frozen approved inputs.

Later wording, only when complete: “Authorize exactly [20–50 count] [LKR or dimensionless] synthetic diagnostic rows using approved [configuration version/hash], [code/source/criterion hashes], and the specified Wedding/Corporate scope. No bulk generation or training authorized.” Do not sign placeholders or substitute a draft hash.

No financial scenarios were generated. Existing source datasets/46-column master and approval records were preserved. Software tests do not establish realistic event economics. **Next requested action: select and review the branch/protocol; do not grant executable pilot permission yet.**
''')
    verification_path = ROOT / 'work/dataset_recovery_verification.json'
    if verification_path.is_file():
        verification = read('work/dataset_recovery_verification.json')
        if not verification['failures'] and not verification['errors'] and not verification['skipped']:
            text = (f"\n## Software and saved-file verification\n\nThe complete suite passed {verification['tests_run']} tests "
                    "with zero failures/errors/skips, including all 90 existing tests. New tests cover grouping/leakage, "
                    "strict expansion counts and dimensionless validation/accounting. No stochastic unitless pilot "
                    "or integrated bulk writer is tested because those paths remain unimplemented. Original engine, "
                    "API/generator files and existing final source-context artifacts match their previous hashes.\n\n"
                    "Saved blocker workbook ZIP/content/cached summary/reviewer blanks were independently reopened and checked; "
                    "both sheets were visually inspected. The authoring process returned a nonzero exit after reporting export; "
                    "saved-file checks passed. Desktop Microsoft Excel interaction/recalculation was not tested.\n")
            for p in ('reports/stage5_recovery_plan.md', 'reports/pilot_approval_decision_packet.md'):
                write(p, (ROOT / p).read_text(encoding='utf-8') + text)
    audit = {'version': VERSION, 'stage_reports_read': stage_reports, 'blockers': blockers,
             'blocker_status_counts': dict(Counter(b['Status'] for b in blockers)),
             'formula_recommendations': dict(Counter(f['recommendation'] for f in tables['formulas'])),
             'numeric_classifications': dict(classification), 'formal_formulas_pending': 19,
             'formal_numeric_reviews_pending': 108, 'original_lkr_config_sha256': sha('config/minimal_pilot_candidate.json'),
             'unitless_draft_sha256': sha('config/unitless_pilot.proposed.json'), 'unitless_numeric_proposal_valid': True,
             'unitless_approvals_present': False, 'lkr_gate_blockers': lkr_reasons, 'unitless_gate_blockers': unitless_reasons,
             'live_engine_status': {e: evaluate(lkr, e)['status'] for e in ('Wedding', 'Corporate')},
             'frozen_configuration_sha256': None, 'pilot_generated': False, 'bulk_generated': False, 'models_trained': False,
             'stage6_passed': False, 'new_code_current_sha256': {p: sha(p) for p in ('component4/dataset_design.py', 'component4/unitless_experiment.py', 'scripts/research_pipeline/audit_split_leakage.py')}}
    write('work/dataset_recovery_audit.json', json.dumps(audit, indent=2, allow_nan=False) + '\n')
    write('reports/split_leakage_validation.json', json.dumps({'version': VERSION, 'actual_dataset_audit_status': 'NOT_PERFORMED_NO_PILOT',
          'current_unseen_template_split': 'BLOCKED_SINGLE_SHARED_VENUE_COMPONENT',
          'conditional_protocol': 'PROPOSED_PENDING_SUPERVISOR_REVIEW', 'software_tests': 'see full-suite verification',
          'machine_readable_cli': 'scripts/research_pipeline/audit_split_leakage.py', 'actual_record_count': None,
          'actual_violations': None, 'actual_validation_pass': False}, indent=2) + '\n')
    print(json.dumps({'blocker_records': len(blockers), 'statuses': audit['blocker_status_counts'],
                      'formulas_pending': 19, 'lkr_gate_codes': len(lkr_reasons), 'unitless_numeric_proposal_valid': True,
                      'stage5_execution_ready': False}, indent=2))


if __name__ == '__main__':
    main()
