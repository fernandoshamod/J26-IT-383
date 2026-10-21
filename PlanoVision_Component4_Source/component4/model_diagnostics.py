"""Read-only error analysis and whole-family learning-curve utilities."""
from collections import defaultdict
import math
import numpy as np
from .expense_risk import FEATURES


def _bounds(pair):
    a,b=pair
    if not 0<a<b or not all(math.isfinite(v) for v in pair):raise ValueError('invalid_uniform_bounds')
    return a,b


def simulator_reference(row,target,assumptions):
    """Conditional risk in the assumed simulator, not an observed-event estimate.

    Cost uses one common multiplier for all line items. Receipt and cost draws
    are independent. Integrating the uniform rectangle is exact before cent
    rounding; small ledger-rounding effects are intentionally disclosed.
    """
    a,b=_bounds(assumptions['ordinary_cost_multiplier'])
    c,d=_bounds(assumptions['receipt_multiplier'])
    cost=row['Planned_Total_Cost_LKR'];receipts=row['Retained_Receipts_LKR']
    if cost<=0 or receipts<=0:raise ValueError('positive_planning_money_required')
    if target=='Budget_Overrun':p=(b-row['Target_Budget_LKR']/cost)/(b-a)
    elif target=='Profit_Margin_Risk':
        threshold=(1-row['Minimum_Margin_Pct']/100)*receipts/cost
        if threshold<=0:raise ValueError('invalid_margin_threshold')
        full=max(0,min(d,a/threshold)-c)
        lo=max(c,a/threshold);hi=min(d,b/threshold)
        partial=(b*(hi-lo)-threshold*(hi*hi-lo*lo)/2)/(b-a) if hi>lo else 0
        p=(full+partial)/(d-c)
    else:raise ValueError('unsupported_target')
    return min(1.,max(0.,float(p)))


def nested_family_subsets(rows,counts,seed):
    """Select all rows of each chosen family; no outcome-driven sampling."""
    if any(r['split']!='train' for r in rows):raise ValueError('training_split_only')
    if counts!=sorted(set(counts)) or any(type(n) is not int or n<=0 or n%2 for n in counts):raise ValueError('increasing_even_family_counts_required')
    events={};by_family=defaultdict(list)
    for r in rows:
        event='Wedding' if r['Event_Type_Wedding']==1 else 'Corporate'
        family=r['Base_Event_ID']
        if family in events and events[family]!=event:raise ValueError('mixed_event_family')
        events[family]=event;by_family[family].append(r)
    rng=np.random.default_rng(seed);order={}
    for event in ('Wedding','Corporate'):
        families=sorted(g for g,v in events.items() if v==event)
        order[event]=list(rng.permutation(families))
        if counts[-1]//2>len(families):raise ValueError('insufficient_event_families')
    result=[]
    for count in counts:
        chosen=set(order['Wedding'][:count//2]+order['Corporate'][:count//2])
        subset=[r for r in rows if r['Base_Event_ID'] in chosen]
        assert len(chosen)==count
        result.append((count,subset,sorted(chosen)))
    return result


def bucket(value,edges):
    previous=None
    for edge in edges:
        if value<edge:return ('-inf' if previous is None else str(previous))+' to '+str(edge)
        previous=edge
    return str(previous)+' to +inf'


def paired_label_ambiguity(rows,target):
    vectors=defaultdict(list)
    for r in rows:vectors[tuple(r[f] for f in FEATURES)].append(r)
    conflicting=[rs for rs in vectors.values() if len({r[target] for r in rs})>1]
    return {'planning_vectors':len(vectors),'conflicting_label_vectors':len(conflicting),
        'rows_in_conflicting_vectors':sum(map(len,conflicting)),
        'interpretation':'Observed synthetic replications with identical full planning features but differing labels; not an estimated universal accuracy ceiling'}


def error_audit(rows,predictions,assumptions,protocol):
    by_id={r['Scenario_ID']:r for r in rows};seen=set();cases=[];summary={}
    if len(by_id)!=len(rows):raise ValueError('duplicate_source_scenario')
    for saved in predictions:
        sid=saved['Scenario_ID'];target=saved['target'];key=(sid,target)
        if key in seen:raise ValueError('duplicate_prediction')
        seen.add(key);r=by_id[sid];score=saved['score']
        if saved['split'] not in ('validation','test') or r['split']!=saved['split'] or saved['label']!=r[target]:raise ValueError('prediction_provenance_mismatch')
        if not math.isfinite(score) or not 0<=score<=1:raise ValueError('invalid_saved_score')
        predicted=int(score>=.5);label=r[target]
        kind='TP' if predicted and label else 'FP' if predicted else 'FN' if label else 'TN'
        reference=simulator_reference(r,target,assumptions)
        distance=r['Planned_Budget_Utilization']-1 if target=='Budget_Overrun' else r['Planned_Margin_Buffer_Pct']
        edges=protocol['budget_distance_bins'] if target=='Budget_Overrun' else protocol['margin_buffer_bins_pp']
        window=protocol['boundary_windows']['budget_utilization_distance_from_1' if target=='Budget_Overrun' else 'margin_buffer_absolute_pp']
        actual_cost=r['simulated_final_cost_lkr'];actual_receipts=r['simulated_receipts_lkr']
        realized_margin=100*(actual_receipts-actual_cost)/actual_receipts
        case={'Scenario_ID':sid,'Base_Event_ID':r['Base_Event_ID'],'split':r['split'],'target':target,
            'prediction_kind':kind,'label':label,'predicted_class':predicted,'uncalibrated_score':score,
            'event_type':'Wedding' if r['Event_Type_Wedding'] else 'Corporate','planning_state':r['planning_state'],
            'outcome_replication':r['outcome_replication'],'boundary_bucket':bucket(distance,edges),
            'near_declared_boundary':abs(distance)<=window,'assumption_implied_probability':reference,
            'within_stochastic_overlap':1e-10<reference<1-1e-10,
            'planning_context':{k:r[k] for k in FEATURES},
            'post_outcome_diagnostic_only':{'simulated_final_cost_lkr':actual_cost,'simulated_receipts_lkr':actual_receipts,
                'realized_margin_pct':realized_margin,'realized_cost_multiplier':actual_cost/r['Planned_Total_Cost_LKR'],
                'realized_receipts_multiplier':actual_receipts/r['Retained_Receipts_LKR'],
                'budget_excess_lkr':max(0,actual_cost-r['Target_Budget_LKR']),
                'margin_shortfall_pp':max(0,r['Minimum_Margin_Pct']-realized_margin)}}
        group=summary.setdefault(target,{}).setdefault(r['split'],{'counts':{k:0 for k in ('TN','FP','FN','TP')},'strata':{},'errors_near_boundary':0,'errors_in_stochastic_overlap':0,'rows_in_stochastic_overlap':0,'error_reference_labels':[]})
        group['counts'][kind]+=1;group['rows_in_stochastic_overlap']+=int(case['within_stochastic_overlap'])
        # Strata retain all-case denominators; never report error counts alone as rates.
        for dimension,value in (('event_type',case['event_type']),('planning_state',str(r['planning_state'])),('boundary_bucket',case['boundary_bucket'])):
            cell=group['strata'].setdefault(dimension,{}).setdefault(value,{'rows':0,'errors':0,'FP':0,'FN':0})
            cell['rows']+=1;cell['errors']+=int(kind in ('FP','FN'))
            if kind in ('FP','FN'):cell[kind]+=1
        if kind in ('FP','FN'):
            group['errors_near_boundary']+=int(case['near_declared_boundary'])
            group['errors_in_stochastic_overlap']+=int(case['within_stochastic_overlap'])
            group['error_reference_labels'].append([reference,label]);cases.append(case)
    for target,partitions in summary.items():
        for split,g in partitions.items():
            expected=[r for r in rows if r['split']==split]
            if sum(g['counts'].values())!=len(expected):raise ValueError('prediction_coverage_incomplete')
            g['paired_label_ambiguity']=paired_label_ambiguity(expected,target)
            missed=[x for x in cases if x['target']==target and x['split']==split and x['prediction_kind']=='FN']
            g['missed_risk_severity']={'count':len(missed),
                'median_budget_excess_lkr':float(np.median([x['post_outcome_diagnostic_only']['budget_excess_lkr'] for x in missed])) if missed else None,
                'median_margin_shortfall_pp':float(np.median([x['post_outcome_diagnostic_only']['margin_shortfall_pp'] for x in missed])) if missed else None}
            g.pop('error_reference_labels')
    return summary,cases
