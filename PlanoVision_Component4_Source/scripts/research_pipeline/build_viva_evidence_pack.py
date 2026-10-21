"""Build an offline evidence viewer from frozen artifacts, with fresh replay checks."""
from pathlib import Path
import csv
import hashlib
import html
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from xgboost import Booster, DMatrix
from component4.expense_risk import audit, FEATURES


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(headers, rows):
    cell = lambda value: html.escape(str(value))
    return '<table><thead><tr>' + ''.join('<th>'+cell(v)+'</th>' for v in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+cell(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'


def main():
    out = ROOT/'outputs/PlanoVision_Viva_Dataset_Evidence_20261021'
    if out.exists():
        raise ValueError('refuse_existing_evidence_directory')
    data = 'data/experiments/v3.0/expense_risk_v3_0_20261015/'
    models = 'outputs/experiments/v3.1/expense_risk_v3_1_20261016/'
    reports = 'reports/experiments/v3.1/expense_risk_v3_1_20261016/'
    source = 'outputs/01a12103-7a09-7331-bb93-9e24a6f05005/hotel_evidence_20261012/evidence_metadata.json'
    rows = read_rows(ROOT/(data+'planning_risk_dataset.jsonl'))
    result = audit(rows, read_rows(ROOT/(data+'financial_line_items.jsonl')), read_rows(ROOT/(data+'provenance.jsonl')))
    summary = read_json(ROOT/(reports+'experiment_summary.json'))
    metadata = read_json(ROOT/(models+'metadata.json'))
    heldout = read_rows(ROOT/(models+'heldout_predictions.jsonl'))
    checksums = read_json(ROOT/(reports+'checksums.json'))
    for relative, expected in checksums.items():
        if digest(ROOT/relative) != expected:
            raise ValueError('frozen_checksum_mismatch:'+relative)
    replay = {}
    for target in ('Budget_Overrun', 'Profit_Margin_Risk'):
        selected = [r for r in rows if r['split']=='test']
        fs = metadata['model_features'][target]
        x = np.array([[r[f] for f in fs] for r in selected], dtype=np.float32)
        model = Booster()
        model.load_model(ROOT/(models+target+'.xgboost.json'))
        dm = DMatrix(x)
        p = model.predict(dm)
        stored = [r for r in heldout if r['target']==target and r['split']=='test']
        assert [r['Scenario_ID'] for r in selected] == [r['Scenario_ID'] for r in stored]
        assert np.allclose(p, [r['score'] for r in stored], atol=1e-8)
        phi = model.predict(dm, pred_contribs=True, approx_contribs=False)
        margins = model.predict(dm, output_margin=True)
        shap = np.load(ROOT/(models+target+'.test_shap.npz'), allow_pickle=False)
        assert np.allclose(phi, shap['contributions'])
        assert np.allclose(phi.sum(axis=1), margins, atol=1e-5)
        accuracy = float(np.mean((p >= .5) == np.array([r[target] for r in selected])))
        assert np.isclose(accuracy, summary['metrics'][target]['test']['xgboost']['accuracy'])
        replay[target] = dict(test_rows=len(selected), prediction_replay='PASS', native_TreeSHAP_replay='PASS', accuracy=accuracy, features=fs)
    result.update(status='PASS_FRESH_DATASET_AUDIT_AND_NATIVE_MODEL_REPLAY', checked_utc=datetime.now(timezone.utc).isoformat(), model_replay=replay, frozen_hashes_verified=len(checksums), fit_performed=False, real_world_validation=False)
    out.mkdir(parents=True)
    originals = out/'originals'
    paths = [source, 'config/lkr_research.v2.0.json', 'config/expense_risk.v3.0.json', 'config/risk_enhancement.v3.1.json', 'component4/expense_risk.py', 'component4/lkr_research.py', 'reports/data_quality_fix_20261021/current_monetary_audit.json', 'reports/robustness/v3_1_frozen_robustness_20261016/robustness_report.md', 'reports/robustness/v3_1_frozen_robustness_20261016/regime_performance.png', 'reports/diagnostics/v3_1_steps1_2_20261016/learning_curves.png', 'reports/PP1_COMPONENT_COMPLETE_DOSSIER_20261021.md']
    paths += [data+name for name in ('planning_risk_dataset.jsonl','financial_line_items.jsonl','provenance.jsonl','manifest.json')]
    paths += [models+name for name in ('Budget_Overrun.xgboost.json','Profit_Margin_Risk.xgboost.json','Budget_Overrun.test_shap.npz','Profit_Margin_Risk.test_shap.npz','metadata.json','protocol.json','selection_decisions.before_test.json','heldout_predictions.jsonl')]
    paths += [reports+name for name in ('experiment_summary.json','independent_verification.json','checksums.json','README.md')]
    for relative in paths:
        target = originals/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, target)
    def link(relative, label):
        return '<a href="originals/'+relative+'">'+html.escape(label)+'</a>'
    def export_csv(name, records):
        with (out/name).open('w', newline='', encoding='utf-8-sig') as stream:
            writer=csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    export_csv('FULL_DATASET_3600_ROWS.csv', rows)
    families = {}
    for row in rows:
        family = families.setdefault(row['Base_Event_ID'], dict(Base_Event_ID=row['Base_Event_ID'], split=row['split'], event_type='Wedding' if row['Event_Type_Wedding'] else 'Corporate', row_count=0))
        family['row_count'] += 1
        assert family['split']==row['split']
    export_csv('FAMILY_SPLIT_PROOF_600_FAMILIES.csv', list(families.values()))
    (out/'FRESH_VERIFICATION.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    sections=[]
    sections.append('<h1>PlanoVision dataset & training evidence</h1><p>Component 04: Spatial-Financial Intelligence and Budget Optimization<br>Prepared for PP1 viva, 21 October 2026</p><p class="note">Evidence-anchored synthetic event outcomes. Zero observed completed-event outcomes. The fresh checks below verify integrity and saved model replay, rather than real-world predictive validity.</p>')
    sections.append('<nav>'+''.join('<a href="#s'+str(i)+'">'+label+'</a>' for i,label in enumerate(['Verification','Sources','Assumptions','Dataset','Split proof','Models','Limits'],1))+'</nav>')
    sections.append('<section id="s1"><h2>1. Fresh verification</h2><p class="pass">PASS: dataset audit, native test predictions and native TreeSHAP replay</p>'+table(['Check','Result'], [('Rows / root families / planning vectors',f"{result['rows']} / {result['families']} / {result['planning_vectors']}"),('Cross-split families',0),('Cross-split exact full feature vectors',0),('Frozen artifact hashes checked',len(checksums)),('Models retrained during checks','No'),('Real completed-event validation','Not available')])+'<p><a href="FRESH_VERIFICATION.json">Open fresh machine-readable verification</a></p></section>')
    evidence=read_json(ROOT/source)
    rate_rows=[(r['Evidence_ID'],r['Provider'],r['Package'],f"LKR {r['Rate_LKR']:,.0f} / {r['Rate_Unit']}",r['Source_URL']) for r in evidence['rates'] if r['Evidence_ID'] in ('HOTEL-PUB-R008','HOTEL-PUB-R004')]
    sections.append('<section id="s2"><h2>2. Where the source references came from</h2><p>Saved public-reference snapshot access date: '+evidence['access_date']+'. Current v3 scenarios use these two profiles. This is a reference transfer into a generic hypothetical event.</p>'+table(['Evidence ID','Provider','Reference','Saved rate','Source URL'],rate_rows)+'<p>'+link(source,'Open original source register')+'</p><p>Advertised rates need dated quotation and scope review. Source pages may change. Supporting hotel references and venue benchmarks are not all training profiles.</p></section>')
    config=read_json(ROOT/'config/lkr_research.v2.0.json')
    assumed=[]
    for key in ('chair_lkr_per_person','table_lkr_per_table','labour_increment_lkr_per_person_hour','venue_fixed_lkr'):
        value=config['assumptions'][key]
        assumed.append((key,value['value'],value['unit'],value['origin']))
    sections.append('<section id="s3"><h2>3. Evidence versus assumptions</h2>'+table(['Parameter','Value','Unit','Provenance'],assumed)+'<p>Reserve, spatial/staffing rules, tax/service treatment and outcome shocks are also documented experimental assumptions. Corporate package allocations are synthetic bookkeeping splits, rather than supplier line prices.</p><p>'+link('config/lkr_research.v2.0.json','Open complete parameter and assumption configuration')+'</p></section>')
    sample=rows[:6]
    cols=['Scenario_ID','Base_Event_ID','split','planning_state','outcome_replication','Planned_Total_Cost_LKR','simulated_final_cost_lkr','Budget_Overrun','Profit_Margin_Risk']
    sections.append('<section id="s4"><h2>4. Actual dataset rows</h2><p>600 families x 3 states x 2 outcomes = 3,600 rows. States: 0 original, 1 add an optional expense, 2 remove an existing optional expense. Below are the six actual records of the first family.</p>'+table(cols,[[r[k] for k in cols] for r in sample])+'<p><a href="FULL_DATASET_3600_ROWS.csv">Open full dataset in Excel</a> &nbsp; '+link(data+'planning_risk_dataset.jsonl','Original JSONL')+' &nbsp; '+link(data+'financial_line_items.jsonl','Itemized ledger')+' &nbsp; '+link(data+'provenance.jsonl','Scenario provenance')+'</p><p>Budget label = simulated final cost exceeds spending limit. Margin label = simulated final margin is below the required minimum. Outcome and ID fields are excluded from model predictors.</p></section>')
    sections.append('<section id="s5"><h2>5. Train / validation / test proof</h2>'+table(['Split','Rows','Families'],[(s,result['split_rows'][s],result['split_roots'][s]) for s in ('train','validation','test')])+'<p>All six related rows of each family stay in one split. The fresh audit recalculates family and full-feature-vector separation from the source files.</p><p><a href="FAMILY_SPLIT_PROOF_600_FAMILIES.csv">Open all 600 family assignments</a> &nbsp; '+link('reports/data_quality_fix_20261021/current_monetary_audit.json','Saved audit including deployed-feature overlap checks')+'</p></section>')
    metric_rows=[]
    for target in replay:
        test=summary['metrics'][target]['test']
        print(target, 'test methods:', list(test))
        x=test['xgboost']
        metric_rows.append((target,', '.join(metadata['model_features'][target]),f"{100*x['accuracy']:.2f}%",str(int(x['tn'])),str(int(x['fp'])),str(int(x['fn'])),str(int(x['tp']))))
    sections.append('<section id="s6"><h2>6. Trained models and fresh replay</h2>'+table(['Target','Selected features','Test accuracy','TN','FP','FN','TP'],metric_rows)+'<p>Each target has 720 test rows from 120 families. Rule baseline accuracy: 95.56% budget and 93.47% margin. The models do not establish consistent superiority over rules. Native TreeSHAP contributions replayed on all test rows with additivity checks.</p><p>'+link(models+'Budget_Overrun.xgboost.json','Budget model artifact')+' &nbsp; '+link(models+'Profit_Margin_Risk.xgboost.json','Margin model artifact')+' &nbsp; '+link(models+'protocol.json','Training protocol')+' &nbsp; '+link(reports+'experiment_summary.json','Full saved metrics')+'</p><p>'+link('config/risk_enhancement.v3.1.json','Five candidate settings and selection policy')+'</p><p>Primary evaluation uses family-grouped nested CV. The prior test-development history is disclosed in the original report.</p></section>')
    sections.append('<section id="s7"><h2>7. Scientific limits to explain honestly</h2><ul><li>Zero observed completed-event outcomes.</li><li>Price scope, taxes, staffing and shock ranges need independent domain validation.</li><li>Existing test split has a development history.</li><li>Risk scores remain uncalibrated for actual events.</li><li>Under the designed coupled-adverse synthetic stress regime, margin accuracy falls to 43.95%.</li></ul><p>'+link('reports/robustness/v3_1_frozen_robustness_20261016/robustness_report.md','Original robustness report')+' &nbsp; '+link(reports+'README.md','Original training explanation')+'</p><h3>What this pack proves</h3><p>The saved dataset exists, follows the recorded family split, reconciles to its ledgers, and the saved trained artifacts reproduce the recorded test predictions and native TreeSHAP. Independent market validity requires actual event outcomes.</p></section>')
    css='body{font:17px/1.6 Segoe UI,Arial,sans-serif;color:#173b47;background:#f3f7f8;max-width:1250px;margin:auto;padding:30px}h1{font-size:36px}h2{font-size:26px}section{background:white;padding:28px;margin:24px 0;border:1px solid #dce6e8;border-radius:12px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:11px;text-align:left;border-bottom:1px solid #dce6e8;vertical-align:top}th{background:#eaf3f2}a{color:#086f80;overflow-wrap:anywhere}nav{display:flex;gap:18px;flex-wrap:wrap}.note{background:#fff6df;padding:18px}.pass{color:#087758;font-weight:700}@media print{body{padding:0;background:white;font-size:12px}section{break-inside:avoid;padding:14px}nav{display:none}table{font-size:10px}}'
    (out/'OPEN_EVIDENCE.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PlanoVision Viva Evidence</title><style>'+css+'</style>'+''.join(sections)+'</html>',encoding='utf-8')
    manifest={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    (out/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for path in out.rglob('*'):
            if path.is_file():
                z.write(path, out.name+'/'+path.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps(dict(status=result['status'],viewer=str(out/'OPEN_EVIDENCE.html'),zip=str(archive),bytes=archive.stat().st_size,sha256=digest(archive),checks=result),indent=2))


if __name__=='__main__':
    main()
