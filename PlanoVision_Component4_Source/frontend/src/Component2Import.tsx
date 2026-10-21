import {useRef,useState} from 'react';
import type {Inputs} from './api';
import {validatePlan} from './planStorage';
export default function Component2Import({state,onImport}:{state:Inputs;onImport:(p:Inputs)=>void}){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const latest=useRef(state);latest.current=state;
  return <details className="component2-import"><summary>Import Component 2 quotations</summary><p>Accepts the proposed <code>component2.quotation_bundle.v1</code> JSON contract. This is a local import adapter—not a live connection, independent verification or a vendor search. Only LKR quotations for this event/date are accepted.</p><label>Component 2 quotation JSON<input disabled={busy} type="file" accept=".json,application/json" onChange={async e=>{
    const file=e.target.files?.[0];e.target.value='';if(!file)return;const snapshot=JSON.stringify(state);setBusy(true);setMessage('');
    try{
      if(file.size>60000)throw Error('Quotation bundle is too large.');
      const text=await file.text();const r=await fetch('/api/planner/component2/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bundle_json:text,state})});
      const data=await r.json();if(!r.ok)throw Error(data.error??'Import failed');
      if(data.contract_version!=='component2.quotation_bundle.v1'||data.status!=='proposed_inputs_only'||data.independently_verified!==false||data.transport_authenticated!==false)throw Error('Invalid Component 2 response.');
      if(JSON.stringify(latest.current)!==snapshot)throw Error('Plan changed while importing. Import again against the current preview.');
      onImport(validatePlan(data.proposed_state));setMessage(`Bundle ${data.bundle_id} imported into preview only. Check tax/date/price-term warnings before confirmation. Supplier declarations are not independently verified.`);
    }catch(err){setMessage('Component 2 import rejected: '+(err as Error).message);}finally{setBusy(false);}
  }}/></label>{busy&&<p role="status">Validating Component 2 quotation bundle…</p>}{message&&<p role="status">{message}</p>}</details>;
}
