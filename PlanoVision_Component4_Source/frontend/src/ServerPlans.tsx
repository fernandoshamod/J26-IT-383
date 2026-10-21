import {useCallback,useEffect,useState,type Dispatch,type SetStateAction} from 'react';
import type {Inputs} from './api';
import {validatePlan} from './planStorage';

type EventRecord={id:string;name:string;client_name:string;plan:Inputs;created_at:string;updated_at:string};
type Listing={storage:'sqlite';records:EventRecord[];revisions:Record<string,number>;saved_id?:string};
export type BackendEventSession={name:string;client:string;selected:string;loaded:string;loadedRevision:number};
export const blankBackendSession=():BackendEventSession=>({name:'',client:'',selected:'',loaded:'',loadedRevision:0});
type SessionState=[BackendEventSession,Dispatch<SetStateAction<BackendEventSession>>];
export default function ServerPlans({plan,ready,onLoad,session}:{plan:Inputs;ready:boolean;onLoad:(p:Inputs)=>void;session?:SessionState}){
  const local=useState(blankBackendSession);
  const [editor,setEditor]=session??local;
  const {name,client,selected,loaded,loadedRevision}=editor;
  const edit=(patch:Partial<BackendEventSession>)=>setEditor(old=>({...old,...patch}));
  const [data,setData]=useState<Listing>({storage:'sqlite',records:[],revisions:{}}),[busy,setBusy]=useState(true),[message,setMessage]=useState(''),[error,setError]=useState(''),[confirm,setConfirm]=useState(false),[query,setQuery]=useState(''),[page,setPage]=useState(0);
  const request=useCallback(async(path='',method='GET',body?:unknown,signal?:AbortSignal)=>{
    setBusy(true);setError('');setMessage('');
    try{
      const response=await fetch('/api/planner/events'+path,{method,headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal});
      const value=await response.json();if(!response.ok)throw Error(value.error||'Backend save failed.');
      if(value.storage!=='sqlite'||!Array.isArray(value.records)||!value.revisions)throw Error('Invalid backend response.');
      for(const r of value.records){validatePlan(r.plan);if(typeof r.id!=='string'||typeof r.name!=='string'||typeof r.client_name!=='string'||!Number.isInteger(value.revisions[r.id])||value.revisions[r.id]<1)throw Error('Invalid event record.');}
      if(signal?.aborted)return null;
      setData(value);return value as Listing;
    }catch(e){if(!signal?.aborted)setError((e as Error).message);return null;}finally{if(!signal?.aborted)setBusy(false);}
  },[]);
  useEffect(()=>{const abort=new AbortController();void request('','GET',undefined,abort.signal);return()=>abort.abort();},[request]);
  const record=data.records.find(r=>r.id===selected);
  const pageSize=5;
  const normalized=query.trim().toLowerCase();
  const matches=data.records.filter(r=>!normalized||[r.name,r.client_name,r.plan.event_type,r.plan.event_date].some(value=>value.toLowerCase().includes(normalized)));
  const pageCount=Math.max(1,Math.ceil(matches.length/pageSize));
  const safePage=Math.min(page,pageCount-1);
  const visible=matches.slice(safePage*pageSize,(safePage+1)*pageSize);
  function selectRecord(r:EventRecord){edit({selected:r.id,name:r.name,client:r.client_name});setConfirm(false);setMessage('');}
  async function save(update:boolean){
    try{
      const p=validatePlan(plan);
      if(!name.trim())throw Error('Enter a saved event name.');
      if(update&&(!record||loaded!==selected||!loadedRevision))throw Error('Load this saved event before updating it.');
      const value=await request(update?'/'+encodeURIComponent(selected):'',update?'PUT':'POST',{record:{name,client_name:client,plan:p},...(update?{expected_revision:loadedRevision}:{})});
      if(value){const id=update?selected:value.saved_id??value.records.find(r=>!data.records.some(old=>old.id===r.id))?.id;if(id)edit({selected:id,loaded:id,loadedRevision:value.revisions[id]});setMessage('Financial event saved in backend SQLite. Inputs persist after browser refresh and server restart.');}
    }catch(e){setError((e as Error).message);}
  }
  return <section className="backend-plans" aria-label="Backend saved financial events">
    <h3>Save event to backend</h3><p className="muted">Saved events load automatically. Store original or confirmed financial inputs in SQLite; unconfirmed What-If previews and predictions are not saved.</p>
    <div className="form-grid"><label>Saved event name<input disabled={busy} maxLength={100} value={name} placeholder="e.g. Wedding quotation A" onChange={e=>edit({name:e.target.value})}/></label><label>Saved event client name<input disabled={busy} maxLength={100} value={client} onChange={e=>edit({client:e.target.value})}/></label></div>
    <div className="button-row"><button className="primary" disabled={busy||!ready||!name.trim()} onClick={()=>save(false)}>Save new event to backend</button><button className="secondary" disabled={busy} onClick={async()=>{if(await request())setConfirm(false);}}>Refresh backend events</button></div>
    <div className="saved-event-browser">
      <div className="saved-event-browser-heading"><div><h3>Find a saved event</h3><p className="muted">Search by event name, client, type or date. Only five results are shown at a time.</p></div><strong>{matches.length} result{matches.length===1?'':'s'}</strong></div>
      <label>Search saved events<input type="search" disabled={busy} value={query} placeholder="Search name, client, type or date" onChange={e=>{setQuery(e.target.value);setPage(0);}}/></label>
      {!busy&&!error&&data.records.length>0&&matches.length===0&&<p>No saved events match this search.</p>}
      <div className="saved-event-list" aria-label="Saved backend events">
        {visible.map(r=><button type="button" className={'saved-event-row '+(selected===r.id?'selected':'')} aria-pressed={selected===r.id} key={r.id} onClick={()=>selectRecord(r)}><span><strong>{r.name}</strong><small>{r.client_name||'Client not entered'} · {r.plan.event_type} · {r.plan.guests} guests</small></span><time>{r.plan.event_date}</time></button>)}
      </div>
      {matches.length>pageSize&&<div className="saved-event-pages"><button className="secondary" disabled={safePage===0} onClick={()=>setPage(Math.max(0,safePage-1))}>← Previous</button><span>Page {safePage+1} of {pageCount}</span><button className="secondary" disabled={safePage>=pageCount-1} onClick={()=>setPage(Math.min(pageCount-1,safePage+1))}>Next →</button></div>}
    </div>
    {!busy&&!error&&!data.records.length&&<p>No saved backend events yet.</p>}
    {record&&<><p>Saved: {record.name} · {record.client_name||'Client not entered'} · {record.plan.event_type} · {record.plan.guests} guests</p>{loaded!==selected&&<p className="muted">Load this event before updating it. Selecting a record does not replace your current plan.</p>}<div className="button-row"><button className="secondary" disabled={busy} onClick={()=>{onLoad(validatePlan(record.plan));edit({loaded:selected,loadedRevision:data.revisions[selected]});setMessage('Saved backend inputs loaded. Recalculating with current models.');}}>Load saved event</button><button className="secondary" disabled={busy||!ready||!name.trim()||loaded!==selected} onClick={()=>save(true)}>Update selected backend event</button><button className="secondary" disabled={busy} onClick={()=>setConfirm(true)}>Delete saved event</button></div></>}
    {confirm&&record&&<div><p>Delete this saved financial record? The database retains a soft-deleted record. This does not cancel a calendar reservation.</p><button className="secondary" disabled={busy} onClick={async()=>{const value=await request('/'+encodeURIComponent(selected),'DELETE',{expected_revision:data.revisions[selected]});if(value){edit({selected:'',...(loaded===selected?{loaded:'',loadedRevision:0}:{})});setConfirm(false);setMessage('Saved financial event deleted from the active list.');}}}>Confirm delete saved event</button><button className="secondary" disabled={busy} onClick={()=>setConfirm(false)}>Keep saved event</button></div>}
    {busy&&<p role="status">Waiting for backend database…</p>}{message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}
    <small>Database: runtime/planner.sqlite3. Same computer only. No login or encryption. Back up the database file with the app stopped. Saving a financial event does not reserve a calendar date.</small>
  </section>;
}
