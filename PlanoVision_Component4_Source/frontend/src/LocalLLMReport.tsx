import {useEffect,useRef,useState} from 'react';
import type {Inputs} from './api';
type Status={version:string;provider:string;model:string;ready:boolean;reason:string;network_scope:string;model_digest?:string};
type Report={version:string;status:string;provider:string;model:string;model_digest:string;engine_facts_sha256:string;engine_facts:{id:string;statement:string}[];draft:{explanations:{fact_id:string;text:string}[];action_ids:string[]};selected_actions:{id:string;title:string;rationale:string}[];financial_values_modified:false;semantic_accuracy_independently_verified:false;scope:string;report_text:string};
export function decodeLLMReport(d:any):Report{
  if(!d||d.version!=='grounded-local-report.0.1'||d.status!=='generated_review_required'||d.provider!=='ollama_local'||d.financial_values_modified!==false||d.semantic_accuracy_independently_verified!==false||!['model','model_digest','engine_facts_sha256','scope','report_text'].every(k=>typeof d[k]==='string')||!Array.isArray(d.engine_facts)||!d.engine_facts.length||d.engine_facts.some((f:any)=>typeof f.id!=='string'||typeof f.statement!=='string')||!Array.isArray(d.draft?.explanations)||!Array.isArray(d.draft?.action_ids)||!Array.isArray(d.selected_actions))throw Error('Invalid local LLM report.');
  const ids=d.engine_facts.map((f:any)=>f.id);const refs=d.draft.explanations.map((p:any)=>p.fact_id);
  if(new Set(ids).size!==ids.length||refs.length!==ids.length||new Set(refs).size!==refs.length||d.draft.explanations.some((p:any)=>!ids.includes(p.fact_id)||typeof p.text!=='string'))throw Error('Invalid LLM fact references.');
  return d;
}
export default function LocalLLMReport({baseline,alternative,ready}:{baseline:Inputs;alternative:Inputs;ready:boolean}){
  const [status,setStatus]=useState<Status|null>(null),[report,setReport]=useState<Report|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const signature=JSON.stringify({baseline,alternative});const latest=useRef(signature);latest.current=signature;
  useEffect(()=>{setReport(null);setError('');},[signature]);
  const check=async()=>{try{const r=await fetch('/api/planner/llm-status');const d=await r.json();if(!r.ok)throw Error(d.error??'Local LLM status unavailable');if(d.version!=='grounded-local-report.0.1'||d.provider!=='ollama_local'||typeof d.ready!=='boolean'||typeof d.model!=='string'||typeof d.reason!=='string')throw Error('Invalid local LLM status');setStatus(d);setError('');}catch(e){setError((e as Error).message);}};
  useEffect(()=>{void check();},[]);
  return <section className="panel"><span className="eyebrow">LOCAL LLM / GROUNDED REPORT DRAFT</span><h2>AI-assisted explanation report</h2><p>The local language model paraphrases server-calculated facts. It cannot update costs, profit, health or saved plans. Check the AI wording against the authoritative engine fact beneath each paragraph.</p>
    <p>Provider: local Ollama · Model: {status?.model??'Checking…'} · {status?.ready?'Installed local model available':status?.reason?.replaceAll('_',' ')??'Checking service'}</p>
    <div className="button-row"><button className="secondary" disabled={busy} onClick={()=>void check()}>Check local LLM</button><button className="primary" disabled={!ready||busy||!status?.ready} onClick={async()=>{const sent=signature;setBusy(true);setError('');setReport(null);try{
      const r=await fetch('/api/planner/llm-report',{method:'POST',headers:{'Content-Type':'application/json'},body:signature});const d=await r.json();if(!r.ok)throw Error(d.error??'Local LLM report unavailable');if(latest.current!==sent)throw Error('Event inputs changed; generate a new report for the current plan.');setReport(decodeLLMReport(d));
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>Generate local AI draft</button></div>
    {busy&&<p role="status">Local model is drafting the explanation. Financial results remain unchanged…</p>}{error&&<p role="alert">{error}. No fake LLM report was substituted.</p>}
    {report&&<><div className="evaluation-disclosure"><strong>AI draft — human review required</strong><p>{report.scope}</p></div>{report.engine_facts.map(f=><div key={f.id} className="baseline-help"><h3>{f.id.replaceAll('_',' ')}</h3><p>{report.draft.explanations.find(p=>p.fact_id===f.id)?.text}</p><p className="muted"><strong>Engine fact:</strong> {f.statement}</p></div>)}{report.selected_actions.map(a=><div key={a.id}><h3>{a.title}</h3><p>{a.rationale}</p></div>)}<p className="hash">Model digest: {report.model_digest}<br/>Engine facts SHA-256: {report.engine_facts_sha256}</p><button className="secondary" onClick={()=>{const u=URL.createObjectURL(new Blob([report.report_text],{type:'text/plain'}));const a=document.createElement('a');a.href=u;a.download='planovision-local-ai-draft.txt';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}}>Download local AI draft</button></>}
    <p className="muted">No external cloud fallback or automatic model download. Missing runtime, incomplete output or unapproved numerical claims produce a visible error. Semantic correctness of paraphrases still requires human review.</p>
  </section>;
}
