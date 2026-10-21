import {useEffect,useState} from 'react';
import type {Comparison} from './api';
import ModelEvidence from './ModelEvidence';
import TrainingEvaluation from './TrainingEvaluation';
import './model-diagnostics.css';

type Target='Budget_Overrun'|'Profit_Margin_Risk';
type Evidence={version:string;model_run:string;sources:Record<string,{path:string;sha256:string}>;
  errors:Record<Target,{counts:{TN:number;FP:number;FN:number;TP:number};near_boundary:number;paired_conflicts:number}>;
  curves:Record<Target,{families:number;train_accuracy:number;validation_accuracy:number;validation_log_loss:number}[]>;
  robustness:Record<string,Record<Target,{cases:number;metrics:{accuracy:number;recall:number}}>>};
const targets:Target[]=['Budget_Overrun','Profit_Margin_Risk'];
const title=(s:string)=>s.replaceAll('_',' ');
const pct=(n:number)=>(100*n).toFixed(2)+'%';
export function validateEvidence(value:unknown):Evidence{
  const d=value as Evidence;
  if(d?.version!=='v3.1-frozen-diagnostics'||d.model_run!=='expense_risk_v3_1_20261016')throw Error('Evidence version mismatch');
  const finite=(n:number)=>{if(!Number.isFinite(n))throw Error('Invalid diagnostic value');};
  const probability=(n:number)=>{finite(n);if(n<0||n>1)throw Error('Invalid diagnostic metric');};
  for(const t of targets){
    const e=d.errors[t];for(const n of [...Object.values(e.counts),e.near_boundary,e.paired_conflicts]){finite(n);if(n<0||!Number.isInteger(n))throw Error('Invalid error count');}
    if(d.curves[t].length!==5)throw Error('Incomplete learning curve');
    for(const r of d.curves[t]){finite(r.families);probability(r.train_accuracy);probability(r.validation_accuracy);finite(r.validation_log_loss);}
  }
  if(Object.keys(d.robustness).length!==4)throw Error('Incomplete robustness evidence');
  for(const regime of Object.values(d.robustness))for(const t of targets){probability(regime[t].metrics.accuracy);probability(regime[t].metrics.recall);finite(regime[t].cases);}
  if(!Object.values(d.sources).length||Object.values(d.sources).some(s=>!s.path||!/^[a-f0-9]{64}$/.test(s.sha256)))throw Error('Invalid evidence provenance');
  return d;
}
const tabs=['Live model inference','Training evaluation','Learning curves','Error analysis','Robustness'] as const;
export default function EvidenceWorkspace({data}:{data:Comparison}){
  const [tab,setTab]=useState<typeof tabs[number]>('Live model inference');
  const [e,setEvidence]=useState<Evidence|null>(null);const [error,setError]=useState('');
  useEffect(()=>{const controller=new AbortController();fetch('/api/planner/model-evidence',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error('Evidence unavailable');return r.json();}).then(v=>setEvidence(validateEvidence(v))).catch(err=>{if(!controller.signal.aborted)setError(String(err.message));});return()=>controller.abort();},[]);
  const matched=data.alternative.model_trace?.run_id===e?.model_run;
  return <section className="evidence-workspace" aria-label="Model evidence workspace">
    <div className="panel evidence-intro"><span className="eyebrow">SAVED MODELS / AUDITABLE RESEARCH EVIDENCE</span><h2>Model Evidence Lab</h2><p>See what was learned, where it fails, and what is still a financial rule.</p>
      <div className="evidence-separation"><div><strong>Financial rules</strong><p>Itemized costs, profit, capacity and the health indicator are calculated—not learned.</p></div><div><strong>Trained XGBoost</strong><p>Saved classifiers estimate budget-overrun and margin-risk scores. Native TreeSHAP explains their predictions.</p></div><div><strong>Hypothetical simulation</strong><p>Monte Carlo and stress tests use assumed shocks, not observed future outcomes.</p></div></div>
      <p className="evaluation-disclosure">Synthetic-event evaluation only · zero observed completed-event outcomes · no real-world accuracy or safety guarantee.</p>
      <nav className="evidence-tabs" aria-label="Model evidence sections">{tabs.map(t=><button className={tab===t?'primary':'secondary'} aria-pressed={tab===t} key={t} onClick={()=>setTab(t)}>{t}</button>)}</nav>
    </div>
    {tab==='Live model inference'&&<ModelEvidence data={data}/>}
    {tab==='Training evaluation'&&<TrainingEvaluation data={data}/>}
    {!tabs.slice(0,2).includes(tab as never)&&<section className="panel diagnostic-content">
      {error?<p role="alert">Verified diagnostics unavailable: {error}. No substitute metrics are displayed.</p>:!e?<p role="status">Loading frozen diagnostic evidence…</p>:<>
        {!matched&&<p className="evaluation-disclosure">These archived diagnostics describe {e.model_run}; they do not validate a different or withheld current prediction.</p>}
        {tab==='Learning curves'&&<><h2>Does more training data help?</h2><p>Grouped training-only subsamples: 30–240 families. Fixed, already selected settings; exploratory post-selection analysis—not a new independent holdout.</p><Figure name="learning-curves.png" alt="Grouped learning curves for accuracy and log loss"/>{targets.map(t=><div key={t}><h3>{title(t)}</h3><div className="table-wrap"><table><thead><tr><th>Training families</th><th>Train accuracy</th><th>Validation accuracy</th><th>Validation log loss ↓</th></tr></thead><tbody>{e.curves[t].map(r=><tr key={r.families}><td>{r.families}</td><td>{pct(r.train_accuracy)}</td><td>{pct(r.validation_accuracy)}</td><td>{r.validation_log_loss.toFixed(4)}</td></tr>)}</tbody></table></div></div>)}<p>More families reduced score error, but did not consistently increase classification accuracy. Fold variability is descriptive—not a confidence interval. No deployed model was replaced.</p></>}
        {tab==='Error analysis'&&<><h2>Where does the model make mistakes?</h2><p>Existing synthetic test: 720 rows in 120 root families. False negative = a simulated risk the model missed. False positive = a risk warning without that simulated outcome.</p><div className="two-col">{targets.map(t=>{const a=e.errors[t];return <article className="evidence-error-card" key={t}><h3>{title(t)}</h3><strong>{a.counts.FP+a.counts.FN} target-specific errors</strong><p>{a.counts.FN} missed risks · {a.counts.FP} false warnings</p><p>{a.near_boundary} errors near the decision boundary; {a.paired_conflicts} planning vectors have conflicting labels across paired outcomes.</p></article>;})}</div><Figure name="error-concentration.png" alt="Error concentration near the financial decision boundaries"/><p>Near-boundary means cost/budget distance within ±0.10 for overrun; margin buffer within ±5 percentage points for margin risk. Diagnostic future outcomes never become model inputs. Stochastic overlap does not prove every error is unavoidable.</p></>}
        {tab==='Robustness'&&<><h2>What happens when assumptions change?</h2><p className="evidence-danger">Important limitation: margin-risk recall falls sharply under adverse shocks. The model cannot guarantee profitability.</p><p>180 targeted configurations from 12 designed families; 135 supported, 45 withheld. Matched comparisons use 9 families and 512 paired outcome draws per case and regime. These are not independent real events or new training records.</p><Figure name="regime-performance.png" alt="Frozen model performance under four hypothetical shock regimes"/><div className="table-wrap"><table><thead><tr><th>Hypothetical regime</th><th>Target</th><th>Matched cases</th><th>Accuracy</th><th>Risk recall</th></tr></thead><tbody>{Object.entries(e.robustness).flatMap(([regime,values])=>targets.map(t=><tr key={regime+t}><td>{title(regime)}</td><td>{title(t)}</td><td>{values[t].cases}</td><td>{pct(values[t].metrics.accuracy)}</td><td>{pct(values[t].metrics.recall)}</td></tr>))}</tbody></table></div><p>This deliberately boundary-heavy grid differs from the original test distribution. Frozen predictors never received future shocks. Shared templates remain; unseen-venue validation is unsupported.</p></>}
        <details><summary>Frozen source files & SHA-256 checksums</summary>{Object.entries(e.sources).map(([key,s])=><p className="hash" key={key}>{s.path}<br/>{s.sha256}</p>)}<p>Read-only archived diagnostics. Serving these reports does not train a model or alter the dataset.</p></details>
      </>}
    </section>}
  </section>;
}
function Figure({name,alt}:{name:string;alt:string}){const [failed,setFailed]=useState(false);return failed?<p role="alert">Verified chart unavailable. Refer to the source-verified table below.</p>:<a href={'/api/planner/evidence-image/'+name} target="_blank" rel="noreferrer" title="Open full-size evidence chart"><img className="diagnostic-chart" src={'/api/planner/evidence-image/'+name} alt={alt} onError={()=>setFailed(true)}/></a>;}
