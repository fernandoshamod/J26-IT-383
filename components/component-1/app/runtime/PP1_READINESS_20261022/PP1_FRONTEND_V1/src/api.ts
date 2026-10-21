import Ajv2020 from 'ajv/dist/2020';
import rawSchema from '../contracts/openapi-1.1.0.json';
import type { components } from './generated/api';
export type Schemas = components['schemas'];
export type Success = Schemas['Success'];
export type Layout = Schemas['Layout'];
export type Optimize = Schemas['Optimize'];
export type Twin = Schemas['TwinReceipt'];
export type Analysis = Schemas['AnalysisReceipt'];
export type LayoutEditDraft = { schema:'LOCAL_LAYOUT_EDIT_DRAFT_V1'; status:'validated_draft'; draft_id:string; run_id:string; layout_id:string; group_id:string; delta_m:number[]; layout_objects:Layout['objects']; verification:{valid:boolean;boundary_containment:boolean;positive_area_overlaps:number;minimum_clearance_required_m:number;minimum_clearance_observed_m:number|null;translated_objects:number;fixed_and_other_objects_unchanged:boolean}; source_image_sha256:string; venue_id:string; venue_version:number; twin_sha256:string; baseline_layout_sha256:string; reviewer_id:string; reason:string; approval_scope:string; persisted_to_frozen_run_history:false; created_at:string };
export class ApiError extends Error { constructor(public reason: string, public details: unknown, public http = 0) { super(reason); } }
const ajv = new Ajv2020({ strict: false, allErrors: true, logger:false });
const definitions = JSON.parse(JSON.stringify(rawSchema.components.schemas).replaceAll('#/components/schemas/', '#/definitions/'));
ajv.addSchema({ $id:'pp1', definitions });
const validators = new Map<string, ReturnType<typeof ajv.compile>>();
export function validate<T extends keyof Schemas>(name: T, data: unknown): Schemas[T] {
  let check = validators.get(name);
  if (!check) { check = ajv.compile({ $ref:`pp1#/definitions/${name}` }); validators.set(name, check); }
  if (!check(data)) throw new ApiError(`CONTRACT_VALIDATION_FAILED: ${name}`, check.errors);
  return data as Schemas[T];
}
export function jsonObject(value: unknown): Record<string, unknown> { if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected a JSON object'); return value as Record<string, unknown>; }
export function artifactUrl(path: string) { if (!path.startsWith('/analyses/') || path.includes('..')) throw new Error('Unexpected artifact URL'); return '/api'+path; }
function verifiedSuccess(data:unknown):Success {
  const r=validate('Success',data),ids=new Set(r.candidate_layouts.map(l=>l.layout_id));
  if(!ids.size||ids.size!==r.candidate_layouts.length||!ids.has(r.selected_layout_id)||r.xai.response_id!==r.run_id||r.xai.selected_layout_id!==r.selected_layout_id)throw new ApiError('INCONSISTENT_SUCCESS_BINDING',r.run_id);
  if(!Array.isArray(r.xai.explanations)||r.xai.explanations.length!==ids.size)throw new ApiError('MISSING_LAYOUT_EXPLANATIONS',r.run_id);
  for(const layout of r.candidate_layouts){
    const m=jsonObject(r.verification[layout.layout_id]);
    const x=r.xai.explanations.map(jsonObject).filter(e=>e.layout_id===layout.layout_id);
    if(m.valid!==true||!layout.constraint_results.independently_verified||typeof m.layout_sha256!=='string'||!/^[0-9a-f]{64}$/.test(m.layout_sha256)||x.length!==1||x[0].layout_sha256!==m.layout_sha256)throw new ApiError('UNVERIFIED_LAYOUT_OR_XAI_BINDING',layout.layout_id);
  }
  return r;
}
async function call(path: string, method='GET', data?:unknown, binary=false): Promise<unknown> {
  const response=await fetch('/api'+path,{ method, headers:data!==undefined?{'Content-Type':binary?'application/octet-stream':'application/json'}:undefined, body:data===undefined?undefined:binary?data as Blob:JSON.stringify(data) });
  const text=await response.text();let body:unknown;
  try { body=JSON.parse(text); } catch { throw new ApiError('BACKEND_UNAVAILABLE_OR_NON_JSON_RESPONSE',text.slice(0,300),response.status); }
  if (!response.ok) { const error=jsonObject(body);throw new ApiError(String(error.reason??'HTTP_ERROR'),error.details??body,response.status); }
  return body;
}
export const api={
  health:async()=>validate('Health',await call('/health')),
  version:async()=> {const data=jsonObject(await call('/contracts'));if(data.api_version!=='1.1.0')throw new ApiError('UNSUPPORTED_BACKEND_VERSION',data.api_version);return data;},
  runs:async()=>validate('RunIndex',await call('/runs')),
  run:async(id:string)=>{const r=validate('StoredRun',await call('/runs/'+encodeURIComponent(id)));if(r.response.status==='success'){verifiedSuccess(r.response);const q=validate('Optimize',r.request);if(q.venue_id!==r.response.venue_id||q.venue_version!==r.response.venue_version||q.twin_sha256!==r.response.twin_sha256)throw new ApiError('STORED_RUN_TWIN_BINDING_MISMATCH',id);}return r;},
  upload:async(file:File)=>validate('ImageReceipt',await call('/images','POST',file,true)),
  analyze:async(path:string)=>validate('AnalysisReceipt',await call('/analyses','POST',validate('Analyze',{image_path:path}))),
  analysis:async(id:string)=>validate('AnalysisReceipt',await call('/analyses/'+encodeURIComponent(id))),
  register:async(input:unknown)=>validate('TwinReceipt',await call('/twins','POST',validate('Register',input))),
  twin:async(id:string,version:number)=>validate('TwinReceipt',await call(`/twins/${encodeURIComponent(id)}/versions/${version}`)),
  optimize:async(input:Optimize)=>{const r=jsonObject(await call('/optimize','POST',validate('Optimize',input)));if(r.status==='success')return verifiedSuccess(r);const denied=validate('NonSuccess',r);if(denied.candidate_layouts.length)throw new ApiError('NON_SUCCESS_CONTAINS_LAYOUTS',denied.run_id);return denied;},
  approve:async(run:string,input:Schemas['Approve'])=>validate('ApprovalReceipt',await call(`/runs/${encodeURIComponent(run)}/approve`,'POST',validate('Approve',input))),
  revoke:async(id:string,input:Schemas['Revoke'])=>validate('RevocationReceipt',await call(`/approvals/${encodeURIComponent(id)}/revoke`,'POST',validate('Revoke',input))),
  validateLayoutEdit:async(input:{run_id:string;layout_id:string;group_id:string;delta_m:number[];reviewer_id:string;reason:string;explicit_permission:boolean}):Promise<LayoutEditDraft>=>{
    const r=await fetch('/companion/layout-edits/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(input)});
    const text=await r.text();let body:unknown;try{body=JSON.parse(text);}catch{throw new ApiError('LAYOUT_EDIT_COMPANION_UNAVAILABLE',text.slice(0,300),r.status);}
    if(!r.ok){const e=jsonObject(body),detail=e.detail&&typeof e.detail==='object'&&!Array.isArray(e.detail)?e.detail as Record<string,unknown>:{};throw new ApiError(String(detail.reason??'LAYOUT_EDIT_REJECTED'),detail.details??e.detail,r.status);}
    const x=jsonObject(body),verification=x.verification&&typeof x.verification==='object'&&!Array.isArray(x.verification)?x.verification as Record<string,unknown>:{};if(x.schema!=='LOCAL_LAYOUT_EDIT_DRAFT_V1'||x.status!=='validated_draft'||!Array.isArray(x.layout_objects)||verification.valid!==true)throw new ApiError('LAYOUT_EDIT_RESPONSE_INVALID',body,r.status);
    return x as unknown as LayoutEditDraft;
  },
};
export function download(name:string,value:unknown) {const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
