"""Create a portable evidence notebook, then execute every cell with Jupyter."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]


def main():
    import nbformat as nb
    out=ROOT/'outputs/PlanoVision_Viva_Dataset_Evidence_20261021'
    cells=[]
    def md(text): cells.append(nb.v4.new_markdown_cell(text))
    def code(text): cells.append(nb.v4.new_code_cell(text.strip()))
    md('# PlanoVision: Dataset and Trained Model Evidence\n\n**Component 04: Spatial-Financial Intelligence and Budget Optimization**\n\nPP1 demonstration. This notebook reads the preserved dataset and models, recalculates data checks, and replays saved test predictions. It does not fit new models.\n\n**Scientific scope:** Evidence-anchored synthetic event outcomes. Zero observed completed-event outcomes. The reported accuracy applies to this synthetic test split.')
    code('''
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, HTML
from xgboost import Booster, DMatrix

here = Path.cwd()
BASE = next(p / 'originals' for p in [here, *here.parents] if (p / 'originals/data').is_dir())
DATA = BASE / 'data/experiments/v3.0/expense_risk_v3_0_20261015'
MODELS = BASE / 'outputs/experiments/v3.1/expense_risk_v3_1_20261016'
REPORTS = BASE / 'reports/experiments/v3.1/expense_risk_v3_1_20261016'
FIGURES = here / 'notebook_figures'
FIGURES.mkdir(exist_ok=True)
df = pd.read_json(DATA / 'planning_risk_dataset.jsonl', lines=True)
metadata = json.loads((MODELS / 'metadata.json').read_text())
summary = json.loads((REPORTS / 'experiment_summary.json').read_text())
targets = ['Budget_Overrun', 'Profit_Margin_Risk']
pd.set_option('display.max_columns', 12)
pd.set_option('display.float_format', lambda v: f'{v:,.3f}')
plt.rcParams.update({'figure.dpi': 125, 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
display(HTML('<style>.dataframe th,.dataframe td{padding:9px!important}.dataframe{font-size:14px}</style>'))
print('Dataset loaded:', len(df), 'rows')
print('Source: preserved originals inside this evidence pack')
''')
    md('## 1. Public source evidence\n\nThese are the saved public rate references used by the current Wedding and Corporate profiles. Advertised references require quotation and scope review. They are not current confirmed supplier quotations.')
    code('''
source = json.loads((BASE / 'outputs/01a12103-7a09-7331-bb93-9e24a6f05005/hotel_evidence_20261012/evidence_metadata.json').read_text())
rates = pd.DataFrame(source['rates'])
print('Saved source access date:', source['access_date'])
display(rates.loc[rates.Evidence_ID.isin(['HOTEL-PUB-R008','HOTEL-PUB-R004']),
    ['Evidence_ID','Provider','Package','Rate_LKR','Rate_Unit','Source_URL']].reset_index(drop=True))
''')
    md('## 2. Documented synthetic assumptions\n\nPublic menu/package rates do not provide a complete event ledger. The following values are experimental parameters. Corporate allocations, tax/service treatment, staffing and spatial rules also require domain validation.')
    code('''
config = json.loads((BASE / 'config/lkr_research.v2.0.json').read_text())
keys = ['chair_lkr_per_person','table_lkr_per_table','labour_increment_lkr_per_person_hour','venue_fixed_lkr']
display(pd.DataFrame([{'Parameter': k, **config['assumptions'][k]} for k in keys]))
print('Cost multiplier assumption:', config['assumptions']['ordinary_cost_multiplier'])
print('Receipt multiplier assumption:', config['assumptions']['receipt_multiplier'])
print('These ranges were not estimated from observed completed-event volatility.')
''')
    md('## 3. Dataset size and scenario design\n\n**600 event families x 3 planning states x 2 outcome replications = 3,600 rows**\n\nState 0: original plan. State 1: add optional expense. State 2: remove existing optional expense.\n\nRows within each family are related, rather than independent completed events.')
    code('''
features = metadata['features']
overview = pd.DataFrame({'Measure':['Outcome rows','Root families','Unique planning vectors','Recorded planning features','Observed completed-event outcomes'],
                         'Value':[len(df),df.Base_Event_ID.nunique(),len(df.drop_duplicates(features)),len(features),0]})
display(overview)
event = np.where(df.Event_Type_Wedding.eq(1), 'Wedding', 'Corporate')
display(pd.crosstab(pd.Series(event, name='Event type'), df['split']).reindex(columns=['train','validation','test']))
''')
    md('## 4. Actual records from one event family\n\nThe following six rows come directly from the preserved dataset. Repeated planning inputs with different simulated outcomes are intentional outcome replications.')
    code('''
sample = df.loc[df.Base_Event_ID.eq(df.iloc[0].Base_Event_ID)]
display(sample[['Scenario_ID','split','planning_state','outcome_replication','Guest_Count','Planned_Total_Cost_LKR','simulated_final_cost_lkr','Budget_Overrun','Profit_Margin_Risk']].reset_index(drop=True))
''')
    md('## 5. Family split and leakage checks\n\nAll versions and outcome replications of one family remain in the same split. Group separation reduces leakage between related records. Shared simulator assumptions still limit independence.')
    code('''
split_order = ['train','validation','test']
split_table = df.groupby('split').agg(Rows=('Scenario_ID','size'), Families=('Base_Event_ID','nunique')).reindex(split_order)
display(split_table)
family_overlap = int(df.groupby('Base_Event_ID')['split'].nunique().gt(1).sum())
full_overlap = int(df.groupby(features, dropna=False)['split'].nunique().gt(1).sum())
projection_checks = []
for target in targets:
    selected = metadata['model_features'][target]
    overlap = int(df.groupby(selected, dropna=False)['split'].nunique().gt(1).sum())
    projection_checks.append({'Target':target,'Cross-split exact model inputs':overlap})
assert family_overlap == full_overlap == 0
assert all(r['Cross-split exact model inputs'] == 0 for r in projection_checks)
print('PASS: cross-split families =', family_overlap)
print('PASS: cross-split full feature vectors =', full_overlap)
display(pd.DataFrame(projection_checks))
fig, ax = plt.subplots(figsize=(7,3.5))
bars=ax.bar(['Train','Validation','Test'],split_table.Rows,color=['#137d78','#4c9baf','#9abac5'])
ax.bar_label(bars,padding=3)
ax.set_ylabel('Synthetic outcome rows')
ax.set_title('Family-based dataset split (60 / 20 / 20)')
ax.set_ylim(0,2500)
fig.tight_layout()
fig.savefig(FIGURES/'01_dataset_split.png',bbox_inches='tight')
plt.show()
''')
    md('## 6. Data quality, labels and financial reconciliation\n\nOnly planning features enter the classifiers. Simulated outcomes, labels, seeds, IDs and split assignments are excluded from model predictors.')
    code('''
missing = int(df[features].isna().sum().sum())
nonfinite = int((~np.isfinite(df[features].to_numpy(dtype=float))).sum())
duplicate_ids = int(df.Scenario_ID.duplicated().sum())
cost_labels = (df.simulated_final_cost_lkr > df.Target_Budget_LKR).astype(int)
final_margin = 100*(df.simulated_receipts_lkr-df.simulated_final_cost_lkr)/df.simulated_receipts_lkr
margin_labels = (final_margin < df.Minimum_Margin_Pct).astype(int)
ledger = pd.read_json(DATA/'financial_line_items.jsonl', lines=True)
sums = ledger.groupby('Scenario_ID')[['planned_lkr','simulated_realized_lkr']].sum().reindex(df.Scenario_ID)
planned_error = float(np.max(np.abs(sums.planned_lkr.to_numpy()-df.Planned_Total_Cost_LKR.to_numpy())))
final_error = float(np.max(np.abs(sums.simulated_realized_lkr.to_numpy()-df.simulated_final_cost_lkr.to_numpy())))
checks = {'Missing numeric features':missing,'Non-finite numeric features':nonfinite,'Duplicate scenario IDs':duplicate_ids,
          'Incorrect budget labels':int((cost_labels!=df.Budget_Overrun).sum()),
          'Incorrect margin labels':int((margin_labels!=df.Profit_Margin_Risk).sum())}
assert all(v==0 for v in checks.values())
assert max(planned_error,final_error) < .011
display(pd.DataFrame({'Check':list(checks),'Count':list(checks.values())}))
print('PASS: planned and simulated line items reconcile to totals within LKR 0.011.')
display(pd.DataFrame({t:df[t].value_counts().reindex([0,1]) for t in targets}).rename_axis('Class'))
''')
    md('## 7. Saved training configuration\n\nThe v3.1 experiment compares five predeclared settings with 3x3 nested family-grouped CV on training families. The existing test split has a development history. See the preserved protocol for the recorded selection policy.')
    code('''
design=json.loads((BASE/'config/risk_enhancement.v3.1.json').read_text())
display(pd.DataFrame(design['candidates']))
display(pd.DataFrame([{'Target':t,'Selected candidate':summary['deployment'][t]['training_cv_winner'],
                       'Actual model inputs':', '.join(metadata['model_features'][t])} for t in targets]))
print('Class threshold:', design['threshold'])
print('Model run:', metadata['run_id'])
''')
    md('## 8. Native model replay and synthetic test results\n\nThis cell loads the original trained XGBoost artifacts and recomputes the saved test predictions. **It performs inference, not training.** Rule baselines appear beside model accuracy.')
    code('''
saved = pd.read_json(MODELS/'heldout_predictions.jsonl', lines=True)
test = df.loc[df['split'].eq('test')].copy()
replay_results=[]
native={}
for target in targets:
    artifact=MODELS/f'{target}.xgboost.json'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==metadata['model_sha256'][target]
    model=Booster()
    model.load_model(artifact)
    x=DMatrix(test[metadata['model_features'][target]].to_numpy(dtype=np.float32))
    scores=model.predict(x)
    previous=saved.loc[saved.target.eq(target)&saved['split'].eq('test')]
    assert list(test.Scenario_ID)==list(previous.Scenario_ID)
    assert np.allclose(scores,previous.score.to_numpy(),atol=1e-8)
    accuracy=float(np.mean((scores>=.5)==test[target].to_numpy()))
    metric=summary['metrics'][target]['test']
    assert np.isclose(accuracy,metric['xgboost']['accuracy'])
    replay_results.append({'Target':target,'Test rows':len(test),'Model accuracy':f'{accuracy:.2%}',
                           'Rule accuracy':f"{metric['planning_rule_class_accuracy']:.2%}",'Native replay':'PASS'})
    native[target]=(model,x,scores)
display(pd.DataFrame(replay_results))
print('PASS: saved model hashes and all held-out test scores match.')
print('Conclusion: the models do not consistently outperform simple financial rules.')
''')
    md('## 9. Confusion matrices\n\nActual class comes from the simulated final outcome. Predicted class uses the fixed score threshold of 0.5. A missed risk appears in the bottom-left cell.')
    code('''
fig,axes=plt.subplots(1,2,figsize=(9,3.8))
for ax,target in zip(axes,targets):
    predicted=(native[target][2]>=.5).astype(int)
    actual=test[target].to_numpy()
    cm=np.array([[np.sum((actual==a)&(predicted==p)) for p in (0,1)] for a in (0,1)])
    ax.imshow(cm,cmap='Blues',vmin=0,vmax=720)
    for (i,j),value in np.ndenumerate(cm):
        ax.text(j,i,str(value),ha='center',va='center',fontsize=20,color='white' if value>360 else '#16374a')
    ax.set_xticks([0,1],['No risk','Risk'])
    ax.set_yticks([0,1],['No risk','Risk'])
    ax.set_xlabel('Predicted class')
    ax.set_ylabel('Actual simulated class')
    ax.set_title(target.replace('_',' '))
fig.suptitle('Synthetic test evaluation: 720 rows per target')
fig.tight_layout()
fig.savefig(FIGURES/'02_confusion_matrices.png',bbox_inches='tight')
plt.show()
''')
    md('## 10. Native TreeSHAP verification\n\nTreeSHAP explains the fitted model output in log-odds. The contributions plus the bias term reproduce the raw prediction. They do not represent causal effects or LKR savings.')
    code('''
shap_checks=[]
for target in targets:
    model,x,scores=native[target]
    phi=model.predict(x,pred_contribs=True,approx_contribs=False)
    margins=model.predict(x,output_margin=True)
    stored=np.load(MODELS/f'{target}.test_shap.npz',allow_pickle=False)
    error=float(np.max(np.abs(phi.sum(axis=1)-margins)))
    assert np.allclose(phi,stored['contributions'])
    assert np.allclose(phi.sum(axis=1),margins,atol=1e-5)
    shap_checks.append({'Target':target,'Rows':len(test),'Saved native SHAP replay':'PASS','Maximum additivity error':error})
display(pd.DataFrame(shap_checks))
print('PASS: native TreeSHAP replay and additivity on the complete test set.')
''')
    md('## 11. Findings and limitations\n\n- Dataset and labels reconcile to the documented simulator.\n- The family split and selected-feature overlap checks pass.\n- Saved trained models reproduce the recorded test predictions.\n- Test scores describe synthetic events and remain uncalibrated for actual events.\n- The rule baseline is competitive with the classifiers.\n- The prior test-development history prevents a new untouched-holdout claim.\n- The saved coupled-adverse stress evaluation reports margin accuracy of 43.95%.\n- Real-event outcomes, supplier scope validation and genuine planner evaluation remain necessary.\n\n**Suggested screenshots:** Section 1 (sources), Section 3 (counts), Section 5 (split proof), Section 6 (quality checks), Section 8 (native test replay), Section 9 (confusion matrices), Section 10 (TreeSHAP).')
    notebook=nb.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'PlanoVision Research Python','language':'python','name':'planovision-viva'},'language_info':{'name':'python','version':sys.version.split()[0]}})
    path=out/'PlanoVision_Dataset_Training_Evidence.ipynb'
    nb.write(notebook,path)
    if '--execute' in sys.argv:
        import os
        from nbclient import NotebookClient
        from jupyter_client import KernelManager
        from jupyter_client.kernelspec import KernelSpecManager
        kernel_dir=out/'.jupyter/share/jupyter/kernels/planovision-viva'
        kernel_dir.mkdir(parents=True,exist_ok=True)
        import json
        (kernel_dir/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'PlanoVision Research Python','language':'python'}),encoding='utf-8')
        os.environ['JUPYTER_RUNTIME_DIR']=str(out/'.jupyter/runtime')
        os.environ['IPYTHONDIR']=str(out/'.jupyter/ipython')
        manager=KernelManager(kernel_name='planovision-viva',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir.parent)]))
        client=NotebookClient(notebook,km=manager,timeout=180,resources={'metadata':{'path':str(out)}})
        try:
            client.execute()
        finally:
            nb.write(notebook,path)
        errors=[output for cell in notebook.cells if cell.cell_type=='code' for output in cell.get('outputs',[]) if output.output_type=='error']
        assert not errors, errors
        from nbconvert import HTMLExporter
        body,_=HTMLExporter().from_notebook_node(notebook)
        (out/'NOTEBOOK_EXECUTED_PREVIEW.html').write_text(body,encoding='utf-8')
        print('PASS: all',sum(c.cell_type=='code' for c in notebook.cells),'code cells executed without errors; native results and charts embedded.')
    print(path)


if __name__=='__main__': main()
