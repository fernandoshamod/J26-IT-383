import {useEffect,useState} from 'react';
type Series={series_id:string;unit:string;selected_model:string;forecast_origin:string;first_replay_month:string;last_replay_month:string;source_id:string;scope:'ingredient_component'|'market_context_only';validation_mae_in_series_unit:number};
type Catalog={version:string;mode:string;series:Series[];limitations:string[]};
type Replay={status:'blocked'|'available_historical_replay';mode:string;series_id:string;unit:string;model:string;forecast_origin:string;last_supported_month:string;target_month:string;forecast_yhat:number|null;ingredient_subtotal_lkr:number|null;applied_to_event_budget:false;calibrated_current_event_forecast:false;reason:string};
export function decodeCatalog(d:any):Catalog{
  if(d?.version!=='historical-forecast-bridge.v1'||d.mode!=='archived_retrospective_replay_only'||!Array.isArray(d.series)||!d.series.length||!Array.isArray(d.limitations)||d.limitations.some((v:unknown)=>typeof v!=='string')||d.series.some((s:any)=>!s||!['series_id','unit','selected_model','forecast_origin','first_replay_month','last_replay_month','source_id'].every(k=>typeof s[k]==='string')||!['ingredient_component','market_context_only'].includes(s.scope)||!Number.isFinite(s.validation_mae_in_series_unit)))throw Error('Invalid historical forecast catalog.');
  return d;
}
export function decodeReplay(d:any):Replay{
  if(!d||!['blocked','available_historical_replay'].includes(d.status)||d.mode!=='archived_retrospective_replay_only'||d.applied_to_event_budget!==false||d.calibrated_current_event_forecast!==false||!['series_id','unit','model','forecast_origin','last_supported_month','target_month','reason'].every(k=>typeof d[k]==='string')||['forecast_yhat','ingredient_subtotal_lkr'].some(k=>d[k]!==null&&!Number.isFinite(d[k]))||d.status==='available_historical_replay'&&!(d.forecast_yhat>0))throw Error('Invalid historical forecast result.');
  return d;
}
export default function HistoricalForecastPanel({eventDate}:{eventDate:string}){
  const [opened,setOpened]=useState(false);
  return <section className="panel"><span className="eyebrow">HISTORICAL FORECASTS / SCOPE-GATED REPLAY</span><h2>Historical price forecasts</h2><p>No automatic event-budget uplift. This viewer replays saved price/index forecasts; it does not predict current vendor packages. Component 2 supplies current quote terms.</p><details onToggle={e=>{if(e.currentTarget.open)setOpened(true);}}><summary>Inspect series, forecast dates & coverage</summary>{opened&&<ForecastForm eventDate={eventDate}/>}</details></section>;
}
export function ForecastForm({eventDate}:{eventDate:string}){
  const [catalog,setCatalog]=useState<Catalog|null>(null),[id,setId]=useState(''),[month,setMonth]=useState(eventDate.slice(0,7)),[quantity,setQuantity]=useState('1'),[error,setError]=useState(''),[busy,setBusy]=useState(false),[result,setResult]=useState<Replay|null>(null);
  useEffect(()=>{const controller=new AbortController();fetch('/api/planner/forecast-catalog',{signal:controller.signal}).then(r=>{if(!r.ok)throw Error('Verified historical forecasts unavailable');return r.json();}).then(v=>{const c=decodeCatalog(v);setCatalog(c);setId(c.series[0].series_id);}).catch(e=>{if(!controller.signal.aborted)setError(e.message);});return()=>controller.abort();},[]);
  const selected=catalog?.series.find(s=>s.series_id===id);
  if(!catalog)return <p role={error?'alert':'status'}>{error||'Loading verified historical series…'}</p>;
  return <div className="forecast-form"><label>Historical series<select disabled={busy} value={id} onChange={e=>{setId(e.target.value);setResult(null);setError('');}}>{catalog.series.map(s=><option key={s.series_id}>{s.series_id}</option>)}</select></label><label>Forecast month<input disabled={busy} type="text" inputMode="numeric" placeholder="YYYY-MM" maxLength={7} value={month} onChange={e=>{setMonth(e.target.value);setResult(null);}}/></label>{selected?.scope==='ingredient_component'&&<label>Quantity in published unit<input disabled={busy} type="number" min="0" step="any" value={quantity} onChange={e=>{setQuantity(e.target.value);setResult(null);}}/></label>}
    <p>Source: {selected?.source_id} · Unit: {selected?.unit} · Validation-selected method: <strong>{selected?.selected_model}</strong> · Model cutoff: {selected?.forecast_origin}</p><p>Archived coverage: {selected?.first_replay_month}–{selected?.last_replay_month}. Monthly keys are not verified publication timestamps. Not every series selected Prophet over the naive baselines.</p>
    <button className="secondary" disabled={busy||!selected} onClick={async()=>{setBusy(true);setError('');setResult(null);try{
      if(!/^\d{4}-\d{2}$/.test(month))throw Error('Choose a valid month.');
      const q=selected!.scope==='ingredient_component'?Number(quantity):null;
      if(q!==null&&(!quantity.trim()||!Number.isFinite(q)||q<=0))throw Error('Enter a positive quantity in the published unit.');
      const r=await fetch('/api/planner/forecast-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({series_id:id,target_month:month+'-01',unit:selected!.unit,quantity:q,expense_scope:selected!.scope})});const d=await r.json();if(!r.ok)throw Error(d.error??'Forecast unavailable');setResult(decodeReplay(d));
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>Check historical forecast coverage</button>
    {busy&&<p role="status">Checking archived forecast…</p>}{error&&<p role="alert">{error}</p>}
    {result&&(result.status==='blocked'?<p role="alert">Forecast not available for this request: {result.reason.replaceAll('_',' ')}. Model cutoff {result.forecast_origin}; last supported month {result.last_supported_month}. No amount was added to the event.</p>:<div className="evaluation-disclosure"><strong>Historical replay only — not a current event forecast</strong><p>Saved {result.model} forecast: {result.forecast_yhat!.toFixed(2)} {result.unit} · {result.target_month}</p>{result.ingredient_subtotal_lkr!==null&&<p>Partial ingredient illustration: LKR {result.ingredient_subtotal_lkr.toFixed(2)}. Not a complete catering package or an extra charge; never automatically added to the existing catering ledger.</p>}<p>No real-world calibration or uncertainty interval is asserted.</p></div>)}
    <details><summary>Historical forecast limitations</summary><ul>{catalog.limitations.map(v=><li key={v}>{v}</li>)}</ul></details>
  </div>;
}
