import {tomorrowLocal} from './eventSetup';

export const BOOKING_KEY='planovision.local-bookings.v1';
export const CALENDAR_KEY='planovision.booking-calendar.v1';
export function rememberedCalendar():string {
  try{const name=localStorage.getItem(CALENDAR_KEY);return typeof name==='string'&&name.trim()&&name.length<=100?name:'';}catch{return '';}
}
export function rememberCalendar(resource:string){
  if(resource.trim()&&resource.length<=100)localStorage.setItem(CALENDAR_KEY,resource.trim().replace(/\s+/g,' '));
}
export type Booking={id:string;resource:string;date:string;label:string;event_type:'Wedding'|'Corporate'|'Unspecified';status:'reserved'|'cancelled';created_at:string;client_name?:string;client_contact?:string;event_category?:string;revision?:number};
export const resourceKey=(value:string)=>value.trim().replace(/\s+/g,' ').toLocaleLowerCase('en');
export function realDate(value:string):boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value))&&new Date(value).toISOString().slice(0,10)===value;
}
export function parseRegister(text:string):Booking[]{
  if(text.length>2000000)throw Error('Booking register is too large.');
  const data=JSON.parse(text);
  if(!data||data.version!==1||Object.keys(data).sort().join(',')!=='bookings,version'||!Array.isArray(data.bookings)||data.bookings.length>2000)throw Error('Invalid booking register.');
  const ids=new Set<string>();
  for(const b of data.bookings){
    if(!b||Object.keys(b).filter(k=>!['client_name','client_contact','event_category','revision'].includes(k)).sort().join(',')!=='created_at,date,event_type,id,label,resource,status'||
       (b.revision!==undefined&&(!Number.isInteger(b.revision)||b.revision<1))||
       !['client_name','client_contact','event_category'].every(k=>b[k]===undefined||(typeof b[k]==='string'&&b[k].length<=100))||
       typeof b.id!=='string'||!b.id||ids.has(b.id)||
       !['resource','label'].every(k=>typeof b[k]==='string'&&b[k].trim().length>0&&b[k].length<=100)||
       typeof b.date!=='string'||!realDate(b.date)||!['Wedding','Corporate','Unspecified'].includes(b.event_type)||
       !['reserved','cancelled'].includes(b.status)||typeof b.created_at!=='string'||!Number.isFinite(Date.parse(b.created_at)))throw Error('Invalid booking record.');
    ids.add(b.id);
    // Preserve legacy date/venue collisions for visible review. New writes and restores
    // enforce the one-event-per-day rule; deleting history is not a migration strategy.
  }
  return data.bookings;
}
export function readBookings():Booking[]{
  const text=localStorage.getItem(BOOKING_KEY);
  return text===null?[]:parseRegister(text);
}
export function conflict(bookings:Booking[],resource:string,date:string):Booking|undefined {
  return bookings.find(b=>b.status==='reserved'&&resourceKey(b.resource)===resourceKey(resource)&&b.date===date);
}
export function dateConflicts(bookings:Booking[],date:string):Booking[]{
  return bookings.filter(b=>b.status==='reserved'&&b.date===date);
}
export function dateConflict(bookings:Booking[],date:string):Booking|undefined {
  return dateConflicts(bookings,date)[0];
}
function writeBookings(bookings:Booking[]){
  const text=JSON.stringify({version:1,bookings});parseRegister(text);
  localStorage.setItem(BOOKING_KEY,text);
}
export function reserveBooking(resource:string,date:string,label:string,eventType='',now=new Date(),clientName=''):Booking[]{
  if(typeof clientName!=='string'||clientName.length>100)throw Error('Client name must be text of at most 100 characters.');
  if(!resource.trim()||!label.trim()||resource.length>100||label.length>100)throw Error('Enter a venue/team name and event reference (maximum 100 characters).');
  if(!realDate(date)||date<tomorrowLocal(now))throw Error('Choose a future event date.');
  // Re-read on every action; never overwrite unreadable or unavailable storage.
  const bookings=readBookings();
  if(dateConflict(bookings,date))throw Error('Already booked locally: your planner calendar allows one event per day, regardless of venue. Choose another date.');
  bookings.push({id:crypto.randomUUID(),resource:resource.trim().replace(/\s+/g,' '),date,label:label.trim(),event_type:['Wedding','Corporate'].includes(eventType)?eventType as Booking['event_type']:'Unspecified',status:'reserved',created_at:now.toISOString(),client_name:clientName.trim()});
  writeBookings(bookings);return bookings;
}
export function changeBooking(id:string,status:Booking['status'],now=new Date()):Booking[]{
  const bookings=readBookings(),booking=bookings.find(b=>b.id===id);
  if(!booking)throw Error('Booking no longer exists; reload the register.');
  if(status==='reserved'&&(booking.date<tomorrowLocal(now)||bookings.some(b=>b.id!==id&&b.status==='reserved'&&b.date===booking.date)))throw Error('Cannot restore: date has passed or another event occupies that day.');
  booking.status=status;writeBookings(bookings);return bookings;
}

export type BookingDetails=Pick<Booking,'date'|'label'|'client_name'|'client_contact'|'event_category'>;
export function updateBookingDetails(id:string,details:BookingDetails,now=new Date()):Booking[]{
  const bookings=readBookings(),booking=bookings.find(b=>b.id===id);
  if(!booking||booking.status!=='reserved')throw Error('Active booking no longer exists; reload the register.');
  if(!realDate(details.date)||details.date<tomorrowLocal(now))throw Error('Choose a future event date.');
  if(bookings.some(b=>b.id!==id&&b.status==='reserved'&&b.date===details.date))throw Error('Cannot save: another event already occupies that day.');
  if(typeof details.label!=='string'||!details.label.trim()||details.label.length>100)throw Error('Enter an event reference (maximum 100 characters).');
  for(const key of ['client_name','client_contact','event_category'] as const){
    if(details[key]!==undefined&&(typeof details[key]!=='string'||details[key]!.length>100))throw Error('Client and event details must be text of at most 100 characters.');
  }
  Object.assign(booking,{date:details.date,label:details.label.trim(),client_name:(details.client_name??'').trim(),client_contact:(details.client_contact??'').trim(),event_category:(details.event_category??'').trim()});
  writeBookings(bookings);return bookings;
}
