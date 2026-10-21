import {useEffect,useRef,useState} from 'react';
import {BOOKING_KEY,readBookings,dateConflict,dateConflicts,resourceKey,realDate,type Booking} from './bookingRegister';
import {bookingService,type MaybePromise} from './bookingService';
import BookedDateNotice from './BookedDateNotice';
import {tomorrowLocal} from './eventSetup';
import './booking-calendar.css';

export default function BookingCalendar({date,eventType,onDateChange}:{date:string;eventType:string;onDateChange:(date:string)=>void}){
  const [resource,setResource]=useState(''),[label,setLabel]=useState(''),[clientName,setClientName]=useState('');
  const [dismissedConflict,setDismissedConflict]=useState('');
  const [justBookedId,setJustBookedId]=useState('');
  const savedMove=useRef('');
  const [saving,setSaving]=useState(false);
  const [bookings,setBookings]=useState<Booking[]>([]),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [month,setMonth]=useState(()=>tomorrowLocal().slice(0,7));
  const today=new Date(),currentYear=today.getFullYear();
  const minimumMonth=`${currentYear}-${String(today.getMonth()+1).padStart(2,'0')}`;
  function browseMonth(value:string){setMonth(value<minimumMonth?minimumMonth:value);}
  function run(task:()=>MaybePromise<Booking[]>,success:(rows:Booking[])=>void,rethrow=false,reading=false):void|Promise<void>{
    setSaving(true);
    const failed=(e:unknown)=>{if(reading)setError('Booking register cannot be read. Availability is unknown; booking is blocked. Existing records were not overwritten.');else{setMessage((e as Error).message);try{const fresh=bookingService.read();if(fresh instanceof Promise)void fresh.then(setBookings).catch(()=>{});else setBookings(fresh);}catch{/* Preserve the displayed records. */}}if(rethrow)throw e;};
    try{const result=task();if(result instanceof Promise)return result.then(success).catch(failed).finally(()=>setSaving(false));success(result);setSaving(false);}
    catch(e){setSaving(false);failed(e);}
  }
  function reload(){return run(()=>bookingService.read(),rows=>{setBookings(rows);setError('');},false,true);}
  useEffect(()=>{reload();const focus=()=>{if(!document.querySelector('.booking-notice[open]'))void reload();};const changed=(e:StorageEvent)=>{if(e.key===BOOKING_KEY||e.key===null)focus();};window.addEventListener('storage',changed);window.addEventListener('focus',focus);return()=>{window.removeEventListener('storage',changed);window.removeEventListener('focus',focus);};},[]);
  useEffect(()=>{if(realDate(date))setMonth(date.slice(0,7)<minimumMonth?minimumMonth:date.slice(0,7));},[date,minimumMonth]);
  const booked=dateConflict(bookings,date);
  const justBooked=!!booked&&justBookedId===booked.id;
  const bookingBlockers=[error,saving?'Waiting for backend storage…':'',
    !resource.trim()?'Enter a venue / team name.':'',
    !label.trim()?'Enter an event reference.':'',
    !realDate(date)?'Select a future event date on the calendar.':'',
    realDate(date)&&date<tomorrowLocal()?'The date must be tomorrow or later.':'',
    booked&&!justBooked?'Your planner calendar already has an event on this date. Changing the venue does not make it available.':''].filter(Boolean);
  useEffect(()=>{const key=date+'|'+resourceKey(resource);setJustBookedId('');if(savedMove.current===key){savedMove.current='';return;}savedMove.current='';setDismissedConflict('');},[date,resourceKey(resource)]);
  const selected=[...bookings].sort((a,b)=>a.date.localeCompare(b.date));
  const first=new Date(Number(month.slice(0,4)),Number(month.slice(5,7))-1,1);
  const days=new Date(first.getFullYear(),first.getMonth()+1,0).getDate();
  const offset=(first.getDay()+6)%7;
  const title=first.toLocaleDateString('en-GB',{month:'long',year:'numeric'});
  const years=Array.from(new Set([...Array.from({length:31},(_,i)=>currentYear+i),first.getFullYear()])).filter(year=>year>=currentYear).sort((a,b)=>a-b);
  function move(delta:number){const next=new Date(first.getFullYear(),first.getMonth()+delta,1);browseMonth(`${next.getFullYear()}-${String(next.getMonth()+1).padStart(2,'0')}`);}
  function updateReservation(b:Booking){
    setJustBookedId('');
    return run(()=>bookingService.status(b,b.status==='reserved'?'cancelled':'reserved'),rows=>{setBookings(rows);setMessage(b.status==='reserved'?'Reservation cancelled in backend; record retained and can be restored.':'Reservation restored in backend.');});
  }
  function exportRegister(){try{const blob=new Blob([JSON.stringify({version:1,bookings:bookings.map(({revision:_,...b})=>b)},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='planovision-backend-bookings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch{setMessage('Booking export failed; no data was changed.');}}
  let legacyCount=0;try{legacyCount=readBookings().length;}catch{/* Keep unreadable browser originals untouched. */}
  return <section className="panel booking-calendar" aria-label="Local booking calendar">
    <span className="eyebrow">LOCAL SCHEDULING / WHOLE-DAY RESERVATIONS</span><h2>Check the date before accepting</h2>
    <p>One event per day across all venues. Reservations save to the local backend SQLite database and reload when you reopen the app. These are planner records, not hotel-confirmed bookings.</p>
    {legacyCount>0&&<details><summary>Previous browser bookings ({legacyCount})</summary><p>Your browser originals remain unchanged. Import is explicit; conflicting legacy dates are reported, not overwritten.</p><button className="secondary" disabled={saving} onClick={async()=>{setSaving(true);try{const r=await bookingService.importLegacy();setBookings(r.rows);setError('');setMessage(r.message);}catch(e){setMessage((e as Error).message);}finally{setSaving(false);}}}>Import previous browser bookings to backend</button></details>}
    <div className="form-grid"><label>Venue / team calendar<input autoComplete="off" name="booking-venue" maxLength={100} placeholder="Enter venue / team name" value={resource} onChange={e=>{setResource(e.target.value);setMessage('');}}/></label><label>Event reference<input maxLength={100} placeholder="e.g. Wedding A — no private client details" value={label} onChange={e=>{setLabel(e.target.value);setJustBookedId('');setMessage('');}}/></label></div>
    <label>Client name (optional)<input autoComplete="off" maxLength={100} placeholder="Enter client name" value={clientName} onChange={e=>setClientName(e.target.value)}/></label>
    <p className="muted">Enter the venue/team for each new event. This field starts blank; previous names are not filled automatically. Date-conflict checks include every venue, not only the typed name.</p>
    <div className="booking-month"><button className="secondary" aria-label="Previous booking month" disabled={month<=minimumMonth} onClick={()=>move(-1)}>←</button><div className="booking-month-selectors"><label>Month<select aria-label="Calendar month" value={month.slice(5,7)} onChange={e=>browseMonth(month.slice(0,4)+'-'+e.target.value)}>{Array.from({length:12},(_,i)=><option key={i} disabled={`${month.slice(0,4)}-${String(i+1).padStart(2,'0')}`<minimumMonth} value={String(i+1).padStart(2,'0')}>{new Date(2026,i,1).toLocaleDateString('en-GB',{month:'long'})}</option>)}</select></label><label>Year<select aria-label="Calendar year" value={String(first.getFullYear())} onChange={e=>browseMonth(e.target.value+'-'+month.slice(5,7))}>{years.map(year=><option key={year} value={year}>{year}</option>)}</select></label></div><button className="secondary" aria-label="Next booking month" onClick={()=>move(1)}>→</button></div>
    <div className="booking-grid" role="group" aria-label={title+' booking dates'}>
      {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(day=><span className="booking-weekday" key={day}>{day}</span>)}
      {Array.from({length:offset},(_,i)=><span key={'empty'+i}/>)}
      {Array.from({length:days},(_,i)=>{const value=`${month}-${String(i+1).padStart(2,'0')}`;const entries=dateConflicts(bookings,value);const entry=entries[0];const past=value<tomorrowLocal();return <button key={value} disabled={past||!!error} aria-pressed={date===value} aria-label={`${value}${entry?' — booked locally':''}`} title={entries.map(b=>b.resource+': '+b.label).join('; ')} className={'booking-day '+(entry?'booked ':'')+(date===value?'selected':'')} onClick={()=>{onDateChange(value);setMessage('');setJustBookedId('');setDismissedConflict('');}}>{i+1}{entry&&<small>{entries.length>1?`Booked (${entries.length})`:'Booked'}</small>}</button>;})}
    </div>
    <p className="muted">Red = saved reservation across any venue · outline = selected · disabled = today/past. Click a date to set the event date. Only explicit reservations create records; browsing dates does not book them.</p>
    {error?<p role="alert" className="error">{error}</p>:justBooked?<div role="status" className="booking-success"><strong>Date successfully booked!</strong><p>{booked!.date} · {booked!.resource} · {booked!.label}</p><small>Reservation saved in backend SQLite. The date will remain marked Booked after refresh or server restart. This is not a hotel/supplier confirmation.</small></div>:booked?<p role="alert" className="error"><strong>Already booked locally — your planner already has an event on this date.</strong> {booked.date}: {booked.resource} · {booked.label}. Choose another date, even if the venue differs.</p>:<p role="status">{realDate(date)?`${date}: no saved planner reservation on this date. Verify external availability before accepting.`:'Select a future date to check saved reservations across all venues.'}</p>}
    {bookingBlockers.length>0&&<div id="booking-requirements" className="muted"><strong>To reserve this date:</strong><ul>{bookingBlockers.map(reason=><li key={reason}>{reason}</li>)}</ul></div>}
    <div className="button-row"><button className="primary" aria-describedby={bookingBlockers.length?'booking-requirements':undefined} disabled={!!booked||bookingBlockers.length>0} onClick={()=>run(()=>bookingService.reserve(resource,date,label,eventType,clientName),rows=>{const saved=dateConflict(rows,date)!;setBookings(rows);setDismissedConflict(saved.id);setJustBookedId(saved.id);setMessage('');})}>Reserve selected date locally</button><button className="secondary" disabled={saving||!!error||!bookings.length} onClick={exportRegister}>Export booking backup</button><button className="secondary" disabled={saving} onClick={reload}>Reload local bookings</button></div>
    {message&&<p role="status">{message}</p>}
    {selected.length>0&&<details><summary>All saved reservations ({selected.filter(b=>b.status==='reserved').length} active)</summary><ul className="booking-list">{selected.map(b=><li key={b.id}><span><strong>{b.date}</strong> · {b.resource} · {b.label} · {b.event_type} · {b.status}</span><button className="secondary" disabled={!!error} onClick={()=>updateReservation(b)}>{b.status==='reserved'?'Cancel reservation':'Restore reservation'}</button></li>)}</ul></details>}
    <p className="muted">Backend database: runtime/planner.sqlite3 on this computer. Financial-plan saves do not reserve dates. SQLite prevents simultaneous active bookings on the same date. Stale edits are rejected using revisions; reload to see another session’s changes. No authentication, remote synchronization or hotel integration is provided. Client information is unencrypted; protect and back up the database.</p>
    {booked&&!justBooked&&!error&&dismissedConflict!==booked.id&&<BookedDateNotice key={booked.id} booking={booked} onReview={()=>setDismissedConflict(booked.id)} onChooseDate={()=>{setDismissedConflict(booked.id);onDateChange('');}} onSave={details=>run(()=>bookingService.update(booked,details),rows=>{if(details.date!==booked.date)savedMove.current=details.date+'|'+resourceKey(resource);setBookings(rows);setDismissedConflict(booked.id);setMessage('Event details saved'+(details.date!==booked.date?' and reservation moved to '+details.date:'')+'.');onDateChange(details.date);},true)} onDelete={()=>run(()=>bookingService.status(booked,'cancelled'),rows=>{setBookings(rows);setDismissedConflict(booked.id);setMessage('Reservation deleted from the calendar. Cancelled record retained for recovery.');},true)}/>}
  </section>;
}
