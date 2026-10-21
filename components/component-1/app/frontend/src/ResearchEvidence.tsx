import { useState } from 'react';
import { AlertTriangle, BookOpenCheck, FlaskConical, ShieldCheck } from 'lucide-react';
import report from './research-evidence-v1.json';

type Tab = 'logic' | 'models' | 'comparisons' | 'sources' | 'api';
const tabs: {id: Tab; label: string}[] = [
  {id:'logic',label:'Eight research logics'},
  {id:'models',label:'Models & datasets'},
  {id:'comparisons',label:'Baseline findings'},
  {id:'sources',label:'Real floorplans'},
  {id:'api',label:'Execution boundary'},
];
const badge = (value: string) => value.includes('PENDING') || value.includes('UNRESOLVED') || value.includes('DESIGN') || value.includes('PARTIAL') ? 'amber' : 'blue';

export default function ResearchEvidence(){
  const [tab,setTab]=useState<Tab>('logic');
  return <div className="research-evidence" data-testid="research-evidence">
    <div className="evidence-banner"><BookOpenCheck size={21}/><div><strong>Saved research evidence, clearly scoped</strong><p>{report.scope_note}</p></div><span>Evidence index v{report.version}</span></div>
    <div className="tabs evidence-tabs" role="tablist">{tabs.map(t=><button key={t.id} role="tab" aria-selected={tab===t.id} className={tab===t.id?'chosen':''} onClick={()=>setTab(t.id)}>{t.label}</button>)}</div>
    {tab==='logic'&&<section className="panel"><div className="section-title"><h2>Eight-logic implementation map</h2><span className="muted">Research scope remains complete; implementation varies by logic.</span></div><div className="logic-grid">{report.logics.map(l=><article className="logic-card" key={l.id}><div><span className="logic-number">L{l.id}</span><strong>{l.name}</strong><span className={`badge ${badge(l.status)}`}>{l.status}</span></div><p>{l.evidence}</p><small>{l.limits}</small></article>)}</div></section>}
    {tab==='models'&&<section className="panel"><h2>Checkpoint-specific evidence</h2><p className="muted">Metrics are protocol-specific. Synthetic and diagnostic results are not real-venue accuracy.</p><div className="evidence-table"><div className="evidence-head"><span>Model / role</span><span>Saved evidence</span><span>Qualification limit</span></div>{report.models.map(m=><article key={m.name}><div><strong>{m.name}</strong><p>{m.role}</p><code>{m.sha256}</code></div><div>{m.metric}</div><div>{m.qualification}</div></article>)}</div></section>}
    {tab==='comparisons'&&<section className="panel"><div className="section-title"><h2>Conventional comparisons and null findings</h2><span className="badge amber">Novelty not established</span></div><div className="evidence-table"><div className="evidence-head"><span>Study</span><span>Matched outcomes</span><span>Interpretation</span></div>{report.comparisons.map(x=><article key={x.study}><div><strong>{x.study}</strong><p>{x.scope}</p></div><div><strong>{x.matched}</strong></div><div>{x.verdict}</div></article>)}</div><div className="notice warning"><AlertTriangle size={17}/><div>No matched result is evidence of algorithmic superiority. The studies are scoped controlled comparisons, not independent venue samples.</div></div></section>}
    {tab==='sources'&&<section className="panel"><div className="section-title"><h2>Actual KNOX and Ravenswood analyses</h2><span className="badge amber">Both remain pending review</span></div><div className="two-col">{report.real_floorplans.map(f=><article className="logic-card" key={f.name}><div><strong>{f.name}</strong><span className="badge amber">{f.twin}</span></div><code>{f.sha256}</code><p>{f.inference}</p><p>Optimizer evaluations: <strong>{f.optimization_evaluations}</strong></p><small>{f.limitation}</small></article>)}</div><div className="notice warning"><ShieldCheck size={17}/><div>Actual model inference is demonstrated. A reviewed metric Twin, physical truth and real-source layout search are not.</div></div></section>}
    {tab==='api'&&<section className="panel"><h2>What “without APIs” means in this implementation</h2><div className="api-boundary-list">{report.api_boundary.map(x=><div key={x.category}><strong>{x.category}</strong><span className={`badge ${x.status.includes('Not satisfied')?'amber':'blue'}`}>{x.status}</span></div>)}</div><p className="muted">The supported statement is that tested inference and optimization run locally without third-party hosted AI/optimization services. Python library APIs and internal localhost HTTP APIs are used. Offline Python socket instrumentation does not prove operating-system-level network isolation.</p></section>}
    <section className="evidence-sources"><FlaskConical size={16}/><div><strong>Evidence source index</strong><p>{report.evidence_sources.join(' · ')}</p></div></section>
  </div>;
}
