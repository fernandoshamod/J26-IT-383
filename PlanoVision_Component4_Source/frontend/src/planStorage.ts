import {validateInputs,type Inputs,type Quote} from './api';
export const PLAN_KEY='planovision.main-plan.v1';
const fields=['event_type','event_date','guests','event_hours','venue_width_m','venue_length_m','target_budget_lkr','retained_receipts_lkr','min_profit_margin_pct','quotes','removed_quote_ids'];
const quoteFields=['id','label','mode','service','quantity_basis','unit_rate_lkr','tax_scope','service_pct','tax_pct','pricing_policy','increase_pct','source_kind','evidence_ref','valid_from','valid_until','covers','committed','cancellation_fee_lkr'];
const exact=(x:unknown,keys:string[])=>!!x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const date=(v:unknown)=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v;
const nullableNumber=(n:unknown)=>n===null||typeof n==='number'&&Number.isFinite(n);
export function validatePlan(value:unknown):Inputs{
  if(!exact(value,fields))throw Error('Invalid main-plan fields. Financial rates, model outputs and approvals cannot be imported.');
  const p=value as Inputs;
  for(const k of fields.filter(k=>!['event_type','event_date','quotes','removed_quote_ids'].includes(k)))if(typeof p[k as keyof Inputs]!=='number')throw Error('Invalid numeric plan input.');
  if(!['Wedding','Corporate'].includes(p.event_type)||!date(p.event_date)||validateInputs(p))throw Error('Invalid event inputs.');
  if(!Array.isArray(p.quotes)||p.quotes.length>30||!Array.isArray(p.removed_quote_ids))throw Error('Invalid expense collection.');
  const ids=new Set<string>();
  for(const q of p.quotes){
    if(!exact(q,quoteFields)||typeof q.id!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(q.id)||ids.has(q.id))throw Error('Invalid or duplicate quotation.');
    ids.add(q.id);
    if(['label','service','evidence_ref'].some(k=>typeof q[k as keyof Quote]!=='string'||!(q[k as keyof Quote] as string).trim()||(q[k as keyof Quote] as string).length>1000)||
       !['add','replace'].includes(q.mode)||!['booking','guests','tables','stage_m2','av_kits','staff_hours','event_hours'].includes(q.quantity_basis)||
       !['all_in','exclusive_declared','unknown'].includes(q.tax_scope)||!['locked','documented_escalation','unknown','planning_estimate'].includes(q.pricing_policy)||
       !['user_supplied_unverified_quote','public_advertisement','planner_entered_assumption'].includes(q.source_kind)||
       !date(q.valid_from)||!date(q.valid_until)||q.valid_from>q.valid_until||typeof q.committed!=='boolean'||
       !['unit_rate_lkr','service_pct','tax_pct','increase_pct','cancellation_fee_lkr'].every(k=>nullableNumber(q[k as keyof Quote]))||
       !Array.isArray(q.covers)||!q.covers.length||q.covers.some(x=>typeof x!=='string'||!x.trim()||x.length>1000)||new Set(q.covers).size!==q.covers.length)throw Error('Invalid quotation terms.');
  }
  if(p.removed_quote_ids.some(x=>typeof x!=='string'||!ids.has(x))||new Set(p.removed_quote_ids).size!==p.removed_quote_ids.length)throw Error('Invalid removed expenses.');
  return structuredClone(p);
}
export function serializePlan(plan:Inputs){return JSON.stringify({format:PLAN_KEY,saved_at:new Date().toISOString(),plan:validatePlan(plan)},null,2);}
export function parsePlan(text:string):Inputs{
  if(text.length>131072)throw Error('Plan file is too large.');
  const envelope=JSON.parse(text);
  if(!exact(envelope,['format','saved_at','plan'])||envelope.format!==PLAN_KEY||typeof envelope.saved_at!=='string'||!Number.isFinite(Date.parse(envelope.saved_at)))throw Error('Unsupported plan-file format.');
  return validatePlan(envelope.plan);
}
export function restorePlan():{plan:Inputs|null;message:string}{
  try{const text=localStorage.getItem(PLAN_KEY);return text?{plan:parsePlan(text),message:'Saved main plan restored. Recalculating with current engine and models; no preview was restored.'}:{plan:null,message:''};}
  catch{return {plan:null,message:'Saved plan could not be read. It was not overwritten; a blank event form is shown. Import a valid backup or explicitly save a replacement.'};}
}
export function savePlan(plan:Inputs):string{
  try{localStorage.setItem(PLAN_KEY,serializePlan(plan));return 'Main plan saved on this browser. Export a JSON backup for another browser, port or laptop.';}
  catch{return 'Main plan is updated in memory, but browser storage failed. Export a JSON backup before closing.';}
}
