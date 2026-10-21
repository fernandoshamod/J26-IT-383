"""Steps 1–2 only: audit frozen errors and fit disposable grouped learning curves."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import importlib.metadata
import json
import numpy as np
from xgboost import DMatrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from component4.enhanced_risk_inference import EnhancedRiskInference
from component4.expense_risk import FEATURES,TARGETS
from component4.risk_enhancement import group_folds,fit,matrix,selected_features
from component4.risk_experiment import metrics
from component4.model_diagnostics import error_audit,simulator_reference,nested_family_subsets
from component4.release_input import sha256


def read(path):return [json.loads(line) for line in path.read_text().splitlines()]


def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)


def jsonl(path,rows):
    with path.open('x',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False)+'\n')


def aggregate(runs):
    result={}
    for target in TARGETS:
        result[target]={}
        for setting in ('current_selected','original_full'):
            curve=[]
            counts=sorted({r['training_families'] for r in runs})
            for n in counts:
                part=[r for r in runs if r['target']==target and r['setting']==setting and r['training_families']==n]
                values={}
                for split in ('train','validation'):
                    for metric in ('accuracy','balanced_accuracy','recall','f1','log_loss','brier_score'):
                        foldmeans=[float(np.mean([r[split][metric] for r in part if r['outer_fold']==fold])) for fold in sorted({r['outer_fold'] for r in part})]
                        values[split+'_'+metric]={'mean':float(np.mean(foldmeans)),'sd_across_fold_means':float(np.std(foldmeans,ddof=1))}
                curve.append({'training_families':n,'training_rows':part[0]['training_rows'],'fits':len(part),**values})
            result[target][setting]=curve
    return result


def draw_curves(summary,path):
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for col,target in enumerate(TARGETS):
        for setting,color,label in (('current_selected','#167e73','Current selected setting'),('original_full','#c9823c','Original full-feature setting')):
            rows=summary[target][setting];x=[r['training_families'] for r in rows]
            for row,metric in ((0,'accuracy'),(1,'log_loss')):
                mean=np.asarray([r['validation_'+metric]['mean'] for r in rows]);sd=np.asarray([r['validation_'+metric]['sd_across_fold_means'] for r in rows])
                axes[row,col].plot(x,mean,'o-',color=color,label=label)
                axes[row,col].fill_between(x,np.maximum(0,mean-sd),mean+sd,color=color,alpha=.1)
        rows=summary[target]['current_selected'];x=[r['training_families'] for r in rows]
        for row,metric in ((0,'accuracy'),(1,'log_loss')):
            axes[row,col].plot(x,[r['train_'+metric]['mean'] for r in rows],'--',color='#75828c',label='Current training (resubstitution)')
            axes[row,col].set_xlabel('Complete training root families per fold');axes[row,col].set_ylabel('Accuracy' if metric=='accuracy' else 'Log-loss (lower is better)')
            axes[row,col].grid(alpha=.2);axes[row,col].legend(fontsize=8)
        axes[0,col].set_title(target.replace('_',' '));axes[0,col].set_ylim(.8,1.01)
    fig.suptitle('Exploratory grouped learning curves — existing TRAIN split only\n3 outer folds × 3 nested subsamples; shaded bands = fold SD, not confidence intervals',fontsize=12)
    fig.savefig(path,dpi=160);plt.close(fig)


def draw_errors(summary,path):
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for ax,target in zip(axes,TARGETS):
        cells=summary[target]['test']['strata']['boundary_bucket'];labels=list(cells)
        labels=sorted(labels,key=lambda s:float(s.split(' to ')[0]));x=np.arange(len(labels))
        fn=np.asarray([100*cells[k]['FN']/cells[k]['rows'] for k in labels]);fp=np.asarray([100*cells[k]['FP']/cells[k]['rows'] for k in labels])
        ax.bar(x,fn,color='#b24e42',label='Missed risk (FN)');ax.bar(x,fp,bottom=fn,color='#dca64d',label='False alarm (FP)')
        for i,key in enumerate(labels):ax.annotate('n='+str(cells[key]['rows']),(i,fn[i]+fp[i]),xytext=(0,4),textcoords='offset points',ha='center',fontsize=9)
        ax.set_xticks(x,labels,fontsize=9);ax.set_ylim(0,max(10,float(np.max(fn+fp))*1.3));ax.set_ylabel('Errors / all rows in bin (%)');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=9)
        ax.set_title(target.replace('_',' '));ax.set_xlabel('Planned cost/budget − 1' if target=='Budget_Overrun' else 'Planned margin − required margin (percentage points)')
    fig.suptitle('Retrospective synthetic test error concentration — unchanged threshold 0.5',fontsize=12)
    fig.savefig(path,dpi=160);plt.close(fig)


def report_error(folder,summary,cases,reference):
    lines=['# Step 1 — frozen-model error audit','',
        'Retrospective diagnosis only. No labels, model thresholds, source data, features or deployed models were changed. All final outcomes below are simulated, not real event records.',
        '', '| Target / split | Rows | False alarms | Missed risks | Errors inside stochastic overlap | Conflicting-label planning vectors |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for target in TARGETS:
        for split in ('validation','test'):
            s=summary[target][split];c=s['counts'];errors=c['FP']+c['FN'];ambiguity=s['paired_label_ambiguity']
            lines.append(f"| {target} / {split} | {sum(c.values())} | {c['FP']} | {c['FN']} | {s['errors_in_stochastic_overlap']} / {errors} | {ambiguity['conflicting_label_vectors']} / {ambiguity['planning_vectors']} |")
    lines+=['','## Where errors occur','', '![Error rates by planning boundary](error_concentration.png)','',
        'Counts use all-case denominators, with related rows retained in their original split. Outcome replications are not independent events. The boundary bins/windows were declared in protocol.json before this audit. They are descriptive, not new classifier thresholds.']
    for target in TARGETS:
        s=summary[target]['test'];c=s['counts'];ref=reference[target]['test']
        lines+=['', '### '+target,'',
            f"Test errors near the predeclared planning boundary: {s['errors_near_boundary']} / {c['FP']+c['FN']}. Test rows in the simulator's mixed-outcome region: {s['rows_in_stochastic_overlap']} / {sum(c.values())}.",
            f"Assumption-implied expected optimal accuracy on these planning contexts: {100*ref['assumption_implied_expected_optimal_accuracy']:.2f}%. This is an expectation under the uniform shock mechanism before cent rounding, NOT a fixed cap on one realized test sample or real-world attainable accuracy.",
            f"Median missed-risk severity: budget excess LKR {s['missed_risk_severity']['median_budget_excess_lkr']}; margin shortfall {s['missed_risk_severity']['median_margin_shortfall_pp']} percentage points.",
            '', '| Example missed risk | Planned cost / budget | Planned margin buffer pp | Model score | Simulated budget excess LKR | Simulated margin shortfall pp |', '| --- | ---: | ---: | ---: | ---: | ---: |']
        key='budget_excess_lkr' if target=='Budget_Overrun' else 'margin_shortfall_pp'
        examples=sorted([r for r in cases if r['target']==target and r['split']=='test' and r['prediction_kind']=='FN'],key=lambda r:r['post_outcome_diagnostic_only'][key],reverse=True)[:5]
        for r in examples:
            p=r['planning_context'];d=r['post_outcome_diagnostic_only']
            lines.append(f"| {r['Scenario_ID']} | {p['Planned_Budget_Utilization']:.4f} | {p['Planned_Margin_Buffer_Pct']:.3f} | {r['uncalibrated_score']:.4f} | {d['budget_excess_lkr']:.2f} | {d['margin_shortfall_pp']:.3f} |")
    lines+=['','## Diagnosis and next action','',
        '- Different labels for identical full planning vectors demonstrate future-outcome ambiguity in the sampled replications. The model cannot see the hidden shock. This does not by itself diagnose a software defect.',
        '- The simulator-reference probabilities integrate the existing independent uniform common-cost and receipt multipliers. They ignore cent rounding and are assumption-based diagnostics, not calibrated model probabilities or real Sri Lankan risks.',
        '- Do not add realized multipliers, final costs/revenue or labels as prediction-time features. They appear only inside the explicitly named post_outcome_diagnostic_only object in error_cases.jsonl.',
        '- Pre-event facts worth collecting in real events include written price locks, cancellation/change-order terms, receipt certainty and verified tax scope. The current generator does not empirically support these proposed predictors; no fabricated columns were added.',
        '- No target relabeling, shock reduction, test-driven threshold search or model promotion was performed. A new research question/feature study would require a separate version and locked evaluation.',
        '- Every error case, including false alarms, is available in error_cases.jsonl. The examples above are the largest missed risks, not a representative sample.',
        '', 'Source: existing v3.1 native held-out prediction files, v3.0 planning/outcome table and frozen v2 uniform shock definitions. Zero observed completed-event outcomes.']
    (folder/'error_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=json.loads((ROOT/'config/model_diagnostics.v0.1.json').read_text());risk=EnhancedRiskInference()
    folder=ROOT/'reports/diagnostics'/p['run_id']
    if folder.exists():raise ValueError('refuse_existing_diagnostic_run')
    old_protocol=json.loads((risk.folder/'protocol.json').read_text());protected=old_protocol['protected_files'].copy()
    for base in (risk.folder,risk.report):protected.update({f.relative_to(ROOT).as_posix():sha256(f) for f in base.rglob('*') if f.is_file()})
    assert all(sha256(ROOT/k)==v for k,v in protected.items())
    source=old_protocol['source_hashes'].copy()
    for name in ('config/model_diagnostics.v0.1.json','component4/model_diagnostics.py','scripts/model_experiments/audit_errors_and_learning_curves.py'):
        source[name]=sha256(ROOT/name)
    folder.mkdir(parents=True)
    save(folder/'protocol.json',{'recorded_before_diagnostics_utc':datetime.now(timezone.utc).isoformat(),'design':p,
        'source_hashes':source,'protected_files':protected,'runtime':{k:importlib.metadata.version(k) for k in ('numpy','scikit-learn','xgboost','matplotlib')},
        'no_model_promotion':True,'no_dataset_generation':True})
    data=ROOT/'data/experiments/v3.0'/p['data_run'];rows=read(data/'planning_risk_dataset.jsonl')
    saved=read(risk.folder/'heldout_predictions.jsonl');assumptions=json.loads((ROOT/'config/lkr_research.v2.0.json').read_text())['assumptions']
    reference={t:{} for t in TARGETS}
    for target in TARGETS:
        for split in ('validation','test'):
            part=[r for r in rows if r['split']==split];pred=[r for r in saved if r['target']==target and r['split']==split]
            assert [r['Scenario_ID'] for r in part]==[r['Scenario_ID'] for r in pred]
            native=risk.models[target].predict(DMatrix(matrix(part,risk.metadata['model_features'][target])))
            assert np.allclose(native,[r['score'] for r in pred],atol=1e-8)
            implied=np.asarray([simulator_reference(r,target,assumptions) for r in part])
            reference[target][split]={'assumption_implied_expected_optimal_accuracy':float(np.mean(np.maximum(implied,1-implied))),
                'model_score_mae_to_assumption_reference':float(np.mean(np.abs(native-implied))),
                'model_reference_decision_disagreements':int(np.sum((native>=.5)!=(implied>=.5))),
                'interpretation':'conditional synthetic reference before cent rounding; not real-world calibration'}
    errors,cases=error_audit(rows,saved,assumptions,p)
    save(folder/'error_audit.json',{'strata_and_counts':errors,'assumption_reference':reference,'case_count':len(cases)})
    jsonl(folder/'error_cases.jsonl',cases)
    print('Frozen prediction/error audit complete:',len(cases),'error records',flush=True)
    training=[r for r in rows if r['split']=='train'];settings=old_protocol['design'];monotonic=risk.design['training']['monotonic_constraints']
    runs=[];membership=[];fit_count=0
    for fold,(tr,va) in enumerate(group_folds(training,p['outer_group_folds'])):
        outer_train=[training[i] for i in tr];valid=[training[i] for i in va];valid_ids=sorted({r['Base_Event_ID'] for r in valid})
        for repeat in range(p['subsample_repeats']):
            subsets=nested_family_subsets(outer_train,p['training_family_counts'],p['seed']+fold*100+repeat)
            for n,subset,ids in subsets:
                assert not set(ids)&set(valid_ids)
                membership.append({'outer_fold':fold,'repeat':repeat,'training_families':n,'training_family_ids':ids,'validation_family_ids':valid_ids,'source_split':'train'})
                for target in TARGETS:
                    deployed=risk.summary['deployment'][target]
                    candidate_id=deployed['training_cv_winner'] if deployed['deployed']=='enhanced_candidate' else 'original_full'
                    current=next(c for c in settings['candidates'] if c['id']==candidate_id)
                    assert selected_features(settings,current,target)==risk.metadata['model_features'][target]
                    for name,candidate in (('current_selected',current),('original_full',settings['candidates'][0])):
                        model=fit(settings,candidate,target,subset,monotonic);fs=selected_features(settings,candidate,target);fit_count+=1
                        tm=metrics([r[target] for r in subset],model.predict_proba(matrix(subset,fs))[:,1])
                        vm=metrics([r[target] for r in valid],model.predict_proba(matrix(valid,fs))[:,1])
                        runs.append({'target':target,'setting':name,'candidate':candidate['id'],'features':fs,
                            'outer_fold':fold,'repeat':repeat,'training_families':n,'training_rows':len(subset),
                            'validation_families':len(valid_ids),'validation_rows':len(valid),'train':tm,'validation':vm,'original_split':'train'})
        print('Learning-curve outer fold complete:',fold+1,flush=True)
    curves=aggregate(runs);jsonl(folder/'learning_curve_runs.jsonl',runs);jsonl(folder/'learning_curve_membership.jsonl',membership)
    save(folder/'learning_curve_summary.json',{'curves':curves,'fits':fit_count,'model_deployment':False,'scope':p['learning_curve_scope'],
        'band_definition':'SD across three outer-fold means after averaging correlated repeats; not independent replications or confidence intervals'})
    draw_curves(curves,folder/'learning_curves.png');draw_errors(errors,folder/'error_concentration.png');report_error(folder,errors,cases,reference)
    lines=['# Step 2 — grouped learning curves','',p['learning_curve_scope'],'',
        '![Exploratory learning curves](learning_curves.png)','',
        '| Target / locked setting | Training families per fold | Train accuracy | CV validation accuracy | CV log-loss |',
        '| --- | ---: | ---: | ---: | ---: |']
    for target in TARGETS:
        for setting in ('current_selected','original_full'):
            for r in curves[target][setting]:lines.append(f"| {target} / {setting} | {r['training_families']} | {100*r['train_accuracy']['mean']:.2f}% | {100*r['validation_accuracy']['mean']:.2f}% | {r['validation_log_loss']['mean']:.5f} |")
        selected=curves[target]['current_selected'];a,b=selected[2],selected[-1]
        lines+=['',f"{target}, 120→240 training families per fold: validation accuracy {100*a['validation_accuracy']['mean']:.2f}%→{100*b['validation_accuracy']['mean']:.2f}%; log-loss {a['validation_log_loss']['mean']:.5f}→{b['validation_log_loss']['mean']:.5f}.",'']
    lines+=['## Interpretation boundaries','',
        '- The x-axis is complete synthetic root families, not rows; six related rows belong to each family. Each outer validation fold has 120 different families / 720 rows drawn only from the original TRAIN split.',
        '- Wedding/Corporate family counts are balanced by design. Sampling is nested and fixed by seed, never by outcome labels. No row-level random split or test-based training selection is used.',
        '- Curves compare fixed post-selection settings, not a nested hyperparameter search at every size. Existing training data previously informed those settings; these curves are exploratory and do not supersede the earlier nested-CV audit.',
        '- Repeated subsets share families and all sizes in a fold use the same validation families. Shaded SD bands are descriptive across three fold means, not confidence intervals or nine independent experiments.',
        '- The largest training subset is 240 families per fold because 120 of the 360 original training families are held out in each fold. No original validation/test families were fitted.',
        '- Increasing-family performance differences suggest whether more same-simulator data may help, but do not prove a plateau, statistical significance or real-world accuracy. More rows from the same family are not more independent evidence.',
        '- All fitted curve models are disposable diagnostics; none is saved over, promoted or substituted for the deployed models. No thresholds, cost assumptions, shock ranges, source data or labels changed.',
        '', '## Re-run safely','',
        'Run `scripts/model_experiments/audit_errors_and_learning_curves.py` from the project Python environment in a clean copy. Existing run directories are rejected to prevent overwriting evidence. Exact sources, seeds, family memberships and runtime are recorded in protocol.json and learning_curve_membership.jsonl.',
        '', 'Method reference: https://scikit-learn.org/stable/modules/learning_curve.html']
    (folder/'learning_curve_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    assert all(sha256(ROOT/k)==v for k,v in protected.items()),'frozen_artifact_changed'
    save(folder/'verification.json',{'status':'PASS','protected_files_unchanged':len(protected),'data_regenerated':False,
        'production_models_changed':False,'heldout_data_used_for_fitting':False,'thresholds_tuned':False,'curve_fits':fit_count,
        'membership_records':len(membership),'error_cases':len(cases),'source_model_run':risk.run_id,
        'interpretation':'Diagnostic software/provenance verification, not empirical economic validation'})
    save(folder/'checksums.json',{f.name:sha256(f) for f in folder.iterdir() if f.is_file()})
    print(json.dumps({'folder':str(folder),'fits':fit_count,'error_cases':len(cases),'protected_files':len(protected),'current_selected_curves':{t:curves[t]['current_selected'] for t in TARGETS}},indent=2),flush=True)


if __name__=='__main__':main()
