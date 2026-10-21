"""Group-safe, training-only model selection for the existing monetary experiment."""
from collections import Counter
import numpy as np
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier
from .expense_risk import FEATURES
from .risk_experiment import metrics


def group_folds(rows,count=3):
    if len({r['Base_Event_ID'] for r in rows})<count:raise ValueError('insufficient_groups')
    if any(r['split']!='train' for r in rows):raise ValueError('model_selection_requires_training_rows_only')
    ids=[r['Scenario_ID'] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate_scenario')
    groups=np.asarray([r['Base_Event_ID'] for r in rows]);folds=[]
    for train,valid in GroupKFold(count).split(np.zeros(len(rows)),groups=groups):
        if set(groups[train])&set(groups[valid]):raise ValueError('cv_group_leakage')
        vectors=lambda ix:{tuple(rows[i][f] for f in FEATURES) for i in ix}
        if vectors(train)&vectors(valid):raise ValueError('cv_predictor_overlap')
        folds.append((train,valid))
    return folds


def selected_features(protocol,candidate,target):
    return FEATURES if candidate['scope']=='full' else protocol['focused_features'][target]


def matrix(rows,features):return np.asarray([[r[f] for f in features] for r in rows],dtype=float)


def fit(protocol,candidate,target,rows,monotonic):
    if any(r['split']!='train' for r in rows):raise ValueError('fit_requires_training_rows_only')
    features=selected_features(protocol,candidate,target)
    options={k:candidate[k] for k in ('n_estimators','max_depth','learning_rate','reg_lambda','min_child_weight')}
    model=XGBClassifier(**options,n_jobs=1,random_state=protocol['seed'],objective='binary:logistic',
        eval_metric='logloss',tree_method='hist',monotone_constraints=tuple(monotonic.get(f,0) for f in features))
    model.fit(matrix(rows,features),np.asarray([r[target] for r in rows]))
    return model


def search(protocol,target,rows,monotonic):
    folds=group_folds(rows,protocol['inner_group_folds']);results=[]
    for candidate in protocol['candidates']:
        losses=[]
        for tr,va in folds:
            train=[rows[i] for i in tr];valid=[rows[i] for i in va]
            model=fit(protocol,candidate,target,train,monotonic)
            m=metrics([r[target] for r in valid],model.predict_proba(matrix(valid,selected_features(protocol,candidate,target)))[:,1])
            losses.append(m['log_loss'])
        results.append({'candidate':candidate['id'],'fold_log_loss':losses,'mean_log_loss':float(np.mean(losses))})
    winner=min(results,key=lambda r:(r['mean_log_loss'],r['candidate']))['candidate']
    return next(c for c in protocol['candidates'] if c['id']==winner),results


def nested(protocol,target,rows,monotonic):
    predictions=np.zeros(len(rows));baseline=np.zeros(len(rows));assignments=[];fold_results=[]
    for fold,(tr,va) in enumerate(group_folds(rows,protocol['outer_group_folds'])):
        train=[rows[i] for i in tr];valid=[rows[i] for i in va]
        winner,inner=search(protocol,target,train,monotonic)
        model=fit(protocol,winner,target,train,monotonic)
        p=model.predict_proba(matrix(valid,selected_features(protocol,winner,target)))[:,1];predictions[va]=p
        old=fit(protocol,protocol['candidates'][0],target,train,monotonic)
        original=old.predict_proba(matrix(valid,FEATURES))[:,1];baseline[va]=original
        fold_results.append({'fold':fold,'chosen_candidate':winner['id'],'train_families':len({r['Base_Event_ID'] for r in train}),
            'validation_families':len({r['Base_Event_ID'] for r in valid}),'inner_search':inner,
            'metrics':metrics([r[target] for r in valid],p)})
        assignments.extend({'Scenario_ID':rows[i]['Scenario_ID'],'Base_Event_ID':rows[i]['Base_Event_ID'],'outer_fold':fold,
                            'target':target,'label':rows[i][target],'score':float(predictions[i]),'original_cv_score':float(baseline[i])} for i in va)
    y=[r[target] for r in rows]
    return {'oof_metrics':metrics(y,predictions),'original_oof_metrics':metrics(y,baseline),'folds':fold_results,
        'accuracy_fold_sd':float(np.std([f['metrics']['accuracy'] for f in fold_results],ddof=1)),
        'scope':'training-family nested CV, not real-event or unseen-template validation'},assignments


def family_intervals(rows,target,score,old,draws,seed):
    """Paired root-cluster bootstrap; never pretend rows are independent events."""
    roots=sorted({r['Base_Event_ID'] for r in rows});y=np.asarray([r[target] for r in rows])
    correct=(np.asarray(score)>=.5)==y;previous=(np.asarray(old)>=.5)==y
    counts=Counter(r['Base_Event_ID'] for r in rows)
    a=np.asarray([np.sum(correct[[i for i,r in enumerate(rows) if r['Base_Event_ID']==g]]) for g in roots])
    b=np.asarray([np.sum(previous[[i for i,r in enumerate(rows) if r['Base_Event_ID']==g]]) for g in roots])
    n=np.asarray([counts[g] for g in roots]);rng=np.random.default_rng(seed);means=[];deltas=[]
    for _ in range(draws):
        chosen=rng.integers(len(roots),size=len(roots));den=n[chosen].sum()
        means.append(float(a[chosen].sum()/den));deltas.append(float((a[chosen]-b[chosen]).sum()/den))
    return {'accuracy_95_interval':np.quantile(means,[.025,.975]).tolist(),
        'accuracy_difference_vs_v3_95_interval':np.quantile(deltas,[.025,.975]).tolist(),
        'resampling_unit':'Base_Event_ID','families':len(roots),'bootstrap_draws':draws,
        'limitation':'Conditional synthetic-family uncertainty only; shared sources/rules and prior holdout inspection remain'}
