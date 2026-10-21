import {parseRegister,readBookings,type Booking,type BookingDetails} from './bookingRegister';

export type MaybePromise<T>=T|Promise<T>;
async function request(path='',method='GET',body?:unknown):Promise<Booking[]>{
  const response=await fetch('/api/planner/bookings'+path,{method,headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});
  const data=await response.json();
  if(!response.ok)throw Error(data.error||'Backend booking request failed.');
  if(data.storage!=='sqlite'||!data.revisions||!Array.isArray(data.records))throw Error('Invalid backend booking response.');
  const rows=parseRegister(JSON.stringify({version:1,bookings:data.records}));
  if(rows.some(b=>!Number.isInteger(data.revisions[b.id])||data.revisions[b.id]<1))throw Error('Missing booking revision.');
  return rows.map(b=>({...b,revision:data.revisions[b.id]}));
}
function record(b:Partial<Booking>){return {resource:b.resource,date:b.date,label:b.label,event_type:b.event_type||'Unspecified',client_name:b.client_name||'',client_contact:b.client_contact||'',event_category:b.event_category||'',status:b.status||'reserved'};}
export const bookingService:{read:()=>MaybePromise<Booking[]>;reserve:(resource:string,date:string,label:string,eventType:string,clientName:string)=>MaybePromise<Booking[]>;update:(b:Booking,d:BookingDetails)=>MaybePromise<Booking[]>;status:(b:Booking,status:Booking['status'])=>MaybePromise<Booking[]>;importLegacy:()=>Promise<{rows:Booking[];message:string}>}={
  read:()=>request(),
  reserve:(resource,date,label,eventType,clientName)=>request('','POST',{record:record({resource,date,label,event_type:['Wedding','Corporate'].includes(eventType)?eventType as Booking['event_type']:'Unspecified',client_name:clientName})}),
  update:(b,details)=>request('/'+encodeURIComponent(b.id),'PUT',{record:record({...b,...details}),expected_revision:b.revision}),
  status:(b,status)=>request('/'+encodeURIComponent(b.id),status==='cancelled'?'DELETE':'PUT',status==='cancelled'?{expected_revision:b.revision}:{record:record({...b,status}),expected_revision:b.revision}),
  importLegacy:async()=>{
    const legacy=readBookings();
    const response=await fetch('/api/planner/bookings/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bookings:legacy.slice(0,200)})});
    const data=await response.json();if(!response.ok)throw Error(data.error||'Import failed.');
    const failed=(data.import_results||[]).filter((r:{status:string})=>r.status==='not_imported');
    const rows=await request();
    return {rows,message:`Browser import reviewed ${Math.min(200,legacy.length)} records. ${failed.length} not imported. Browser originals were kept.`+(failed.length?' '+failed.map((r:{reason:string})=>r.reason).join(' '):'')+(legacy.length>200?' Export the remaining legacy records for manual review.':'')};
  }
};
