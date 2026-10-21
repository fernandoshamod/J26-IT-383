import {useEffect,useRef,useState} from 'react';
import type {Booking,BookingDetails} from './bookingRegister';
import {tomorrowLocal} from './eventSetup';

export default function BookedDateNotice({booking,onReview,onChooseDate,onSave,onDelete}:{booking:Booking;onReview:()=>void;onChooseDate:()=>void;onSave?:(details:BookingDetails)=>void|Promise<void>;onDelete?:()=>void|Promise<void>}){
  const dialog=useRef<HTMLDialogElement>(null);
  const [details,setDetails]=useState<BookingDetails>({date:booking.date,label:booking.label,client_name:booking.client_name??'',client_contact:booking.client_contact??'',event_category:booking.event_category||(booking.event_type==='Unspecified'?'':booking.event_type)});
  const [error,setError]=useState(''),[confirmDelete,setConfirmDelete]=useState(false);
  const [saving,setSaving]=useState(false);
  useEffect(()=>{
    const node=dialog.current;if(!node)return;
    // Native modal traps focus and makes the background inert. jsdom uses open for tests.
    if(typeof node.showModal==='function'){if(!node.open)node.showModal();}
    else node.setAttribute('open','');
    return()=>{if(typeof node.close==='function'&&node.open)node.close();};
  },[]);
  return <dialog ref={dialog} className="booking-notice" role="alertdialog" aria-modal="true" aria-labelledby="booking-notice-title" aria-describedby="booking-notice-description" onCancel={e=>{e.preventDefault();onReview();}}>
    <div className="booking-notice-top"><span className="eyebrow">SAVED LOCAL RESERVATION</span><button type="button" className="secondary" aria-label="Close event details" autoFocus onClick={onReview}>Close ×</button></div><h2 id="booking-notice-title">This date is already booked</h2>
    <p><strong>{booking.date}</strong> · {booking.resource}</p><p>{booking.event_type}: {booking.label}</p>
    {onSave&&<form className="booking-details" onSubmit={async e=>{e.preventDefault();setSaving(true);try{await onSave(details);setError('');}catch(err){setError((err as Error).message);}finally{setSaving(false);}}}>
      <label>Client name<input maxLength={100} value={details.client_name} onChange={e=>setDetails({...details,client_name:e.target.value})}/></label>
      <label>Client contact (optional)<input maxLength={100} value={details.client_contact} onChange={e=>setDetails({...details,client_contact:e.target.value})}/></label>
      <label>Booked event type<input maxLength={100} placeholder="Wedding, Corporate, Birthday…" value={details.event_category} onChange={e=>setDetails({...details,event_category:e.target.value})}/></label>
      <label>Booking event reference<input required maxLength={100} value={details.label} onChange={e=>setDetails({...details,label:e.target.value})}/></label>
      <label>Move event to date<input required type="date" min={tomorrowLocal()} value={details.date} onChange={e=>setDetails({...details,date:e.target.value})}/></label>
      {error&&<p role="alert" className="error">{error}</p>}
      <button className="primary" disabled={saving} type="submit">Save event details / move date</button>
    </form>}
    <p id="booking-notice-description">Your planner calendar allows one event per day across all venues. Choose a different date for a new event. You may still recalculate the existing event’s budget. Reviewing costs does not create, move or cancel a reservation.</p>
    <div className="button-row"><button className="primary" onClick={onReview}>Review existing event</button><button className="secondary" onClick={onChooseDate}>Choose another date</button></div>
    {onDelete&&<div className="booking-delete">{confirmDelete?<><p>Delete this reservation and free the date? The cancelled record will remain recoverable.</p><button className="secondary" disabled={saving} onClick={async()=>{setSaving(true);try{await onDelete();}catch(err){setError((err as Error).message);}finally{setSaving(false);}}}>Confirm delete reservation</button><button className="secondary" disabled={saving} onClick={()=>setConfirmDelete(false)}>Keep reservation</button></>:<button className="secondary" onClick={()=>setConfirmDelete(true)}>Delete reservation</button>}</div>}
    <p className="muted">This is a local backend record, not verified hotel availability. Closing discards unsaved edits. The duplicate-booking block remains after closing this notice.</p>
  </dialog>;
}
