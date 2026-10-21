"""Explicit planning-only LKR -> graph mapping, unrelated to old score units."""
from collections import Counter
import hashlib
import json
import numpy as np
from .expense_risk import FEATURES

NODES=['Event demand','Venue','Furniture','Stage','Catering','AV','Staffing','Optional services','Financial plan']
MAPPING=[['Guest_Count','Event_Hours','Event_Type_Wedding','Event_Type_Corporate'],
         ['Venue_Area_m2','Space_Utilization','Quoted_Venue_LKR'],
         ['Seating_Count','Quoted_Equipment_LKR'],['Stage_Area_m2'],
         ['Guest_Count','Quoted_Catering_LKR','Reference_Rate_LKR_Per_Person'],
         ['Stage_Area_m2','Quoted_AV_LKR'],['Staff_Count','Paid_Person_Hours','Quoted_Labour_LKR'],
         ['Optional_Expense_Total_LKR','Optional_Expense_Count','Optional_Expense_Fraction'],
         ['Target_Budget_LKR','Retained_Receipts_LKR','Contingency_Reserve_LKR','Minimum_Margin_Pct',
          'Planned_Total_Cost_LKR','Planned_Budget_Utilization','Planned_Margin_Buffer_Pct']]
EDGES=np.asarray([[0,2],[0,4],[0,6],[1,2],[3,5],[1,8],[2,8],[3,8],[4,8],[5,8],[6,8],[7,8]],dtype=np.int64).T
UNITS={k:('LKR' if k.endswith('_LKR') else 'LKR/person' if k=='Reference_Rate_LKR_Per_Person' else
          'm2' if k.endswith('_m2') else 'person_hours' if k=='Paid_Person_Hours' else
          'hours' if k=='Event_Hours' else 'percentage_points' if k.endswith('_Pct') else
          'binary' if k.startswith('Event_Type_') else 'ratio' if k in ('Space_Utilization','Optional_Expense_Fraction','Planned_Budget_Utilization') else 'count') for k in FEATURES}


def schema():
    return {'version':'lkr-planning-dependency-graph.0.1','nodes':NODES,'features':FEATURES,
            'feature_units':UNITS,'node_feature_mapping':dict(zip(NODES,MAPPING)),
            'edges':EDGES.T.tolist(),'edge_semantics':'functional planning dependencies, not observed CAD adjacency',
            'monetary_input_unit':'LKR','old_unitless_model_reused':False}


def vector_graph(row):
    if not isinstance(row,dict) or any(k not in row for k in FEATURES):raise ValueError('complete_planning_feature_vector_required')
    values=np.asarray([row[k] for k in FEATURES],dtype=float)
    if any(isinstance(row[k],bool) for k in FEATURES) or not np.isfinite(values).all():raise ValueError('finite_numeric_planning_features_required')
    x=np.full((len(NODES),len(FEATURES)),np.nan,dtype=float);mask=np.zeros(x.shape,dtype=bool)
    for n,names in enumerate(MAPPING):
        for name in names:
            i=FEATURES.index(name);x[n,i]=values[i];mask[n,i]=True
    return x,mask


def validate_rows(rows):
    ids=set();families={};fingerprints={}
    for r in rows:
        if r['Scenario_ID'] in ids:raise ValueError('duplicate_scenario_id')
        ids.add(r['Scenario_ID'])
        split=r['split'];family=r['Base_Event_ID']
        if split not in ('train','validation','test') or not family:raise ValueError('invalid_split_or_family')
        if family in families and families[family]!=split:raise ValueError('family_crosses_split')
        families[family]=split
        x,m=vector_graph(r);key=hashlib.sha256(np.where(m,x,0).astype('<f8').tobytes()+m.tobytes()).hexdigest()
        if key in fingerprints and fingerprints[key]!=split:raise ValueError('exact_graph_input_crosses_split')
        fingerprints[key]=split
        if any(type(r[t]) is not int or r[t] not in (0,1) for t in ('Budget_Overrun','Profit_Margin_Risk')):raise ValueError('binary_simulated_targets_required')
    return {'rows':dict(Counter(r['split'] for r in rows)),'families':dict(Counter(families.values())),
            'unique_planning_graphs':len(fingerprints),'family_leakage':False,'exact_input_leakage':False}
