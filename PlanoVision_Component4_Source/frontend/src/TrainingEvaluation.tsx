import type {Comparison,ModelMetrics} from './api';
const pct=(n:number)=>(100*n).toFixed(2)+'%';
const title=(s:string)=>s.replaceAll('_',' ');

export default function TrainingEvaluation({data}:{data:Comparison}){
  const e=data.alternative.model_trace?.evaluation;
  if(!e)return null;
  return <section className="panel training-evaluation" aria-label="Model training evaluation">
    <span className="eyebrow">RESEARCH EVIDENCE / GROUP-SAFE MODEL SELECTION</span>
    <h2>Training quality, not just an accuracy number</h2>
    <p>{e.selection}. Final decision threshold: {e.threshold}.</p>
    <div className="evaluation-protocol"><div><strong>360 training families</strong><span>Inner folds select features & regularization</span></div><div><strong>3 outer validation folds</strong><span>Nested out-of-fold performance</span></div><div><strong>120 existing test families</strong><span>Retrospective audit only · 720 related rows</span></div></div>
    <p className="evaluation-disclosure">{e.test_scope}. The holdout was previously inspected. No new untouched holdout or real-event accuracy is claimed. Same source dataset, labels and split assignments; test was not used for this run's selection.</p>
    <div className="evaluation-targets">{Object.entries(e.targets).map(([target,v])=>{
      const m=v.test.xgboost,old=v.test.original_v3,delta=100*(m.accuracy-old.accuracy);
      const low=v.test.family_bootstrap.accuracy_95_interval;
      return <article className="evaluation-card" key={target}>
        <h3>{title(target)}</h3><p className="evaluation-candidate">{v.deployment.training_cv_winner} · {v.features.length} model feature{v.features.length===1?'':'s'}</p>
        <div className="evaluation-numbers"><div><strong>{pct(v.nested_cv.oof_metrics.accuracy)}</strong><span>Nested CV accuracy</span></div><div><strong>{pct(m.accuracy)}</strong><span>Existing test accuracy</span></div></div>
        <p className={delta<0?'metric-tradeoff':'metric-gain'}>v3 test {pct(old.accuracy)} → v3.1 {pct(m.accuracy)} ({delta>=0?'+':''}{delta.toFixed(2)} percentage points)</p>
        <p>Family-bootstrap 95% interval: <strong>{pct(low[0])}–{pct(low[1])}</strong></p>
        <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Previous v3</th><th>Current v3.1</th></tr></thead><tbody>{(['precision','recall','f1','roc_auc','log_loss','brier_score'] as (keyof ModelMetrics)[]).map(k=><tr key={k}><td>{title(k)}{k==='log_loss'||k==='brier_score'?' ↓ lower better':''}</td><td>{old[k].toFixed(4)}</td><td>{m[k].toFixed(4)}</td></tr>)}<tr><td>Planning-rule accuracy</td><td colSpan={2}>{pct(v.test.planning_rule_class_accuracy)}</td></tr><tr><td>Constant-prior accuracy</td><td colSpan={2}>{pct(v.test.prior.accuracy)}</td></tr></tbody></table></div>
        <h4>Confusion matrix · existing synthetic test</h4><p className="muted">Rows: simulated outcome. Columns: predicted class. Positive = risk.</p>
        <table className="confusion-matrix"><thead><tr><th>Outcome / prediction</th><th>No risk</th><th>Risk</th></tr></thead><tbody><tr><th>No risk</th><td className="cm-correct">TN {m.tn}</td><td className="cm-error">FP {m.fp}</td></tr><tr><th>Risk</th><td className="cm-error">FN {m.fn}</td><td className="cm-correct">TP {m.tp}</td></tr></tbody></table>
        <details><summary>Selection, ablation & event-type breakdown</summary><p>Used model features: {v.features.join(', ')}. Other financial/spatial fields still drive the accounting and capacity checks.</p><p>Nested fold accuracies: {v.folds.map(f=>pct(f.accuracy)).join(' / ')}. Fold SD: {(100*v.nested_cv.accuracy_fold_sd).toFixed(2)} percentage points—not a confidence interval.</p><table><thead><tr><th>Training-only candidate</th><th>Mean inner-CV log-loss</th></tr></thead><tbody>{v.training_search.map(c=><tr key={c.candidate}><td>{c.candidate}</td><td>{c.mean_log_loss.toFixed(4)}</td></tr>)}</tbody></table>{Object.entries(v.test.by_event_type).map(([event,a])=><p key={event}>{event}: accuracy {pct(a.accuracy)}, risk recall {pct(a.recall)}</p>)}<p>Validation deployment gate: {v.deployment.validation_gate_pass?'passed':'failed; original model retained'}. Selection was fixed before test reporting.</p></details>
      </article>;
    })}</div>
    <p className="muted">Zero observed completed-event outcomes. Shared vendor/source assumptions; no unseen-venue/provider validation. Bootstrap resamples root families, not individual rows; intervals describe only this simulator. Accuracy improvements are not guaranteed or established as statistically significant. Scores remain uncalibrated.</p>
    <details><summary>Reproducibility identity</summary><p style={{overflowWrap:'anywhere'}}>Training protocol SHA-256: {e.protocol_sha256}</p><p>Original dataset run: {e.source_run}</p><p>Split families: {Object.entries(e.split_roots).map(([k,v])=>`${k} ${v}`).join(' / ')}. Split rows: {Object.entries(e.split_rows).map(([k,v])=>`${k} ${v}`).join(' / ')}.</p></details>
  </section>;
}
