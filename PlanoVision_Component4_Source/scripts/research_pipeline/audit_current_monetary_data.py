"""Re-audit current LKR training data without editing rows, fitting or resetting splits."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.expense_risk import audit,FEATURES
from component4.historical_source_review import sha

def run():
    base=ROOT/'data/experiments/v3.0/expense_risk_v3_0_20261015'
    paths=[base/name for name in ('planning_risk_dataset.jsonl','financial_line_items.jsonl','provenance.jsonl','manifest.json')]
    before={str(p.relative_to(ROOT)):sha(p) for p in paths}
    def lines(path):return [json.loads(line) for line in path.read_text().splitlines()]
    rows,ledger,provenance=map(lines,paths[:3]);result=audit(rows,ledger,provenance)
    if any(isinstance(r[k],bool) or not isinstance(r[k],(int,float)) or not math.isfinite(r[k]) for r in rows for k in FEATURES):raise ValueError('nonfinite_or_missing_planning_feature')
    if any(r['split'] not in {'train','validation','test'} or r['planning_state'] not in {0,1,2} for r in rows):raise ValueError('invalid_split_or_planning_state')
    if any(not math.isfinite(r[k]) or r[k]<=0 for r in rows for k in ('simulated_final_cost_lkr','simulated_receipts_lkr')):raise ValueError('invalid_simulated_financial_outcome')
    if any(not math.isfinite(item[k]) or item[k]<0 for item in ledger for k in ('planned_lkr','simulated_realized_lkr')):raise ValueError('invalid_ledger_amount')
    states=defaultdict(list)
    for r in rows:states[(r['Base_Event_ID'],r['planning_state'])].append(r)
    if any({r['outcome_replication'] for r in part}!={0,1} or len({tuple(r[k] for k in FEATURES) for r in part})!=1 for part in states.values()):raise ValueError('outcome_replication_contract')
    if any(p['origin']!='evidence_anchored_synthetic_not_observed' for p in provenance):raise ValueError('mislabelled_synthetic_origin')
    projections={}
    for target,columns in [('Budget_Overrun',['Planned_Budget_Utilization']),('Profit_Margin_Risk',['Planned_Margin_Buffer_Pct','Minimum_Margin_Pct'])]:
        signatures=defaultdict(set)
        for row in rows:signatures[tuple(row[c] for c in columns)].add(row['split'])
        overlaps=sum(len(partitions)>1 for partitions in signatures.values())
        if overlaps:raise ValueError('deployed_predictor_projection_overlap:'+target)
        projections[target]={'columns':columns,'unique_inputs':len(signatures),'cross_split_exact_inputs':overlaps}
    result.update(status='PASS_CURRENT_SYNTHETIC_DATA_INTEGRITY',created_utc=datetime.now(timezone.utc).isoformat(),
        class_counts={target:dict(Counter(r[target] for r in rows)) for target in ('Budget_Overrun','Profit_Margin_Risk')},
        same_inputs_different_simulated_labels={target:sum(len({r[target] for r in part})>1 for part in states.values()) for target in ('Budget_Overrun','Profit_Margin_Risk')},
        numeric_feature_missing_or_nonfinite=0,labels_and_ledgers_reconciled=True,
        deployed_predictor_projections=projections,
        original_rows_and_splits_changed=False,models_refitted=False,source_hashes=before,
        limitations=['Synthetic outcomes, not genuine completed events.','Previously inspected test set, not a new independent holdout.',
                     'Cost/tax/staffing/shock assumptions remain unverified market parameters; integrity is not empirical validity.',
                     'Identical planning inputs can have different outcome labels under paired hypothetical shocks.'])
    if before!={str(p.relative_to(ROOT)):sha(p) for p in paths}:raise ValueError('audit_changed_data')
    out=ROOT/'reports/data_quality_fix_20261021';out.mkdir(exist_ok=True)
    (out/'current_monetary_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':run()
