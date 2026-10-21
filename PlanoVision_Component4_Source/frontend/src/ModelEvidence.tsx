import type {Comparison} from './api';

export default function ModelEvidence({data}:{data:Comparison}){
  const trace=data.alternative.model_trace;
  if(!trace)return <p className="muted">Model execution evidence unavailable; no inference claim is made.</p>;
  return <section className="panel" aria-label="Trained model execution evidence">
    <span className="eyebrow">SAVED MODEL / ACTUAL REQUEST</span>
    <h2>Actual trained-model inference</h2>
    <p><strong>{trace.prediction_executed?'Native XGBoost prediction executed':'Prediction withheld — unsupported configuration'}</strong></p>
    <p>Run: <code>{trace.run_id}</code></p>
    <p>{trace.training_rows.toLocaleString()} training rows · {trace.test_rows.toLocaleString()} held-out test rows · {trace.independent_root_families} total synthetic root families</p>
    {trace.model_features&&<p className="muted">The 26-field record is the available planning context. The selected compact models use only: {Object.entries(trace.model_features).map(([target,fields])=>`${target}: ${fields.join(', ')}`).join('; ')}. Venue/guest inputs still drive cost and capacity calculations upstream.</p>}
    {trace.support_reasons.length>0&&<p role="status">Withheld: {trace.support_reasons.join('; ')}</p>}
    <div className="table-wrap"><table><thead><tr><th>Risk target</th><th>Original score → preview score</th><th>Synthetic test accuracy</th><th>Planning-rule accuracy</th></tr></thead><tbody>
      {Object.entries(trace.test_metrics).map(([target,m])=><tr key={target}><td>{target.replaceAll('_',' ')}</td><td>{data.baseline.model_scores?.[target]?.uncalibrated_score.toFixed(4)??'Unavailable'} → {data.alternative.model_scores?.[target]?.uncalibrated_score.toFixed(4)??'Unavailable'}</td><td>{(m.xgboost.accuracy*100).toFixed(2)}%</td><td>{(m.planning_rule_class_accuracy*100).toFixed(2)}%</td></tr>)}
    </tbody></table></div>
    <p className="muted">Scores are uncalibrated, not real-world probabilities. This synthetic experiment does not demonstrate a classification-accuracy advantage over simple planning rules. Costs and the health indicator remain separate accounting rules.</p>
    <details><summary>Available planning feature record ({trace.feature_count} fields)</summary>{trace.input_features?<table><tbody>{Object.entries(trace.input_features).map(([key,v])=><tr key={key}><td>{key}</td><td>{v.toLocaleString(undefined,{maximumFractionDigits:6})}</td></tr>)}</tbody></table>:<p>No valid model input vector.</p>}</details>
    <details><summary>Model identity, validation and limitations</summary><p>Method: {trace.method}. Native TreeSHAP additivity: {trace.shap_additivity_verified?'verified for this request':'not executed'}.</p><p style={{overflowWrap:'anywhere'}}>Design SHA-256: {trace.design_sha256}</p>{Object.entries(trace.model_sha256).map(([k,v])=><p key={k} style={{overflowWrap:'anywhere'}}>{k} SHA-256: {v}</p>)}<ul>{trace.limitations.map(v=><li key={v}>{v}</li>)}</ul></details>
  </section>;
}
