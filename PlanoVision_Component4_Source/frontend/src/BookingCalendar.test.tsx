import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import {useState} from 'react';
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import BookingCalendar from './BookingCalendar';
import {BOOKING_KEY,CALENDAR_KEY,readBookings,reserveBooking,changeBooking,updateBookingDetails,parseRegister,conflict,rememberCalendar} from './bookingRegister';
import {tomorrowLocal} from './eventSetup';

// TEST ONLY synchronous store adapter. Production bookingService uses real HTTP/SQLite.
vi.mock('./bookingService',async()=>{const local=await import('./bookingRegister');return {bookingService:{read:local.readBookings,reserve:(r:string,d:string,l:string,e:string,c:string)=>local.reserveBooking(r,d,l,e,new Date(),c),update:(b:import('./bookingRegister').Booking,d:import('./bookingRegister').BookingDetails)=>local.updateBookingDetails(b.id,d),status:(b:import('./bookingRegister').Booking,s:import('./bookingRegister').Booking['status'])=>local.changeBooking(b.id,s),importLegacy:vi.fn()}};});

beforeEach(()=>localStorage.clear());
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const now=new Date(2026,9,19,12);
describe('Local booking register',()=>{
  it('saves client details and moves the same record without changing financial state',()=>{
    const [b]=reserveBooking('Hall','2026-11-05','A','Wedding',now);
    const details={date:'2026-11-07',label:'Updated wedding',client_name:'Test client',client_contact:'test@example.invalid',event_category:'Wedding reception'};
    const rows=updateBookingDetails(b.id,details,now);
    expect(rows).toHaveLength(1);expect(rows[0]).toMatchObject({...details,id:b.id,resource:'Hall',created_at:b.created_at});
    expect(conflict(rows,'Hall','2026-11-05')).toBeUndefined();
    expect(conflict(readBookings(),'Hall','2026-11-07')?.id).toBe(b.id);
  });
  it('rejects occupied/past move destinations and invalid metadata without changing storage',()=>{
    const [b]=reserveBooking('Hall A','2026-11-05','A','Wedding',now);
    reserveBooking('Hall B','2026-11-07','B','Corporate',now);
    const original=localStorage.getItem(BOOKING_KEY);
    for(const details of [{date:'2026-11-07',label:'A'},{date:'2026-10-19',label:'A'},{date:'2026-11-06',label:''},{date:'2026-11-06',label:'A',client_name:'x'.repeat(101)}])expect(()=>updateBookingDetails(b.id,details,now)).toThrow();
    expect(localStorage.getItem(BOOKING_KEY)).toBe(original);
  });
  it('reserves a future day without modifying the financial plan',()=>{
    localStorage.setItem('planovision.main-plan.v1','unchanged');
    const rows=reserveBooking(' Grand   Hall ','2026-10-22','Wedding A','Wedding',now);
    expect(rows).toHaveLength(1);expect(readBookings()).toEqual(rows);
    expect(conflict(rows,'grand hall','2026-10-22')?.label).toBe('Wedding A');
    expect(localStorage.getItem('planovision.main-plan.v1')).toBe('unchanged');
  });
  it('rejects duplicate resource/date even with whitespace and case differences',()=>{
    reserveBooking('Grand Hall','2026-10-22','A','Wedding',now);
    const original=localStorage.getItem(BOOKING_KEY);
    expect(()=>reserveBooking(' GRAND  HALL ','2026-10-22','B','Corporate',now)).toThrow(/Already booked/);
    expect(localStorage.getItem(BOOKING_KEY)).toBe(original);
  });
  it('blocks the same date across different venues but allows different dates',()=>{
    reserveBooking('Hall A','2026-10-22','A','Wedding',now);
    expect(()=>reserveBooking('Hall B','2026-10-22','B','Wedding',now)).toThrow(/one event per day/);
    expect(reserveBooking('Hall B','2026-10-23','C','Corporate',now)).toHaveLength(2);
  });
  it('cancels recoverably and prevents restoration over a replacement reservation',()=>{
    const [a]=reserveBooking('Hall','2026-10-22','A','Wedding',now);
    expect(changeBooking(a.id,'cancelled',now)[0].status).toBe('cancelled');
    expect(changeBooking(a.id,'reserved',now)[0].status).toBe('reserved');
    changeBooking(a.id,'cancelled',now);reserveBooking('Hall','2026-10-22','B','Wedding',now);
    expect(()=>changeBooking(a.id,'reserved',now)).toThrow(/Cannot restore/);
    expect(readBookings()).toHaveLength(2);
  });
  it('blocks past, today, invalid dates and blank resources/references',()=>{
    for(const date of ['2026-10-18','2026-10-19','2026-02-30','no-date'])expect(()=>reserveBooking('Hall',date,'A','Wedding',now)).toThrow();
    expect(()=>reserveBooking('','2026-10-22','A','Wedding',now)).toThrow();
    expect(()=>reserveBooking('Hall','2026-10-22','','Wedding',now)).toThrow();
    expect(readBookings()).toEqual([]);
  });
  it('allows standalone scheduling without mislabelling a birthday as a financial archetype',()=>{
    reserveBooking('Hall A','2026-10-22','Birthday party','',now);
    reserveBooking('Hall B','2026-10-23','Birthday party','Birthday',now);
    expect(readBookings().map(b=>b.event_type)).toEqual(['Unspecified','Unspecified']);
    expect(()=>reserveBooking('Hall A','2026-10-22','Another birthday','',now)).toThrow(/Already booked/);
  });
  it('never overwrites corrupt or unavailable storage',()=>{
    localStorage.setItem(BOOKING_KEY,'corrupt');
    expect(()=>reserveBooking('Hall','2026-10-22','A','Wedding',now)).toThrow();
    expect(localStorage.getItem(BOOKING_KEY)).toBe('corrupt');
    vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw Error('denied');});
    expect(()=>readBookings()).toThrow('denied');
  });
  it('does not claim success if writing storage fails',()=>{
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota');});
    expect(()=>reserveBooking('Hall','2026-10-22','A','Wedding',now)).toThrow('quota');
    expect(readBookings()).toEqual([]);
  });
  it('rejects duplicate identifiers/injected fields but retains legacy collisions for review',()=>{
    const rows=reserveBooking('Hall','2026-10-22','A','Wedding',now);
    for(const bookings of [[...rows,...rows],[{...rows[0],approval:true}]])expect(()=>parseRegister(JSON.stringify({version:1,bookings}))).toThrow();
    expect(parseRegister(JSON.stringify({version:1,bookings:[rows[0],{...rows[0],id:'legacy-other'}]}))).toHaveLength(2);
  });
});

describe('Booking calendar UI',()=>{
  it('closes details after a successful move without reopening the same booking as a new conflict',()=>{
    const day=tomorrowLocal();reserveBooking('TEST hall',day,'Disposable move test','Wedding');
    function Calendar(){const [date,setDate]=useState(day);return <BookingCalendar date={date} eventType="Wedding" onDateChange={setDate}/>;}
    render(<Calendar/>);
    fireEvent.change(screen.getByLabelText('Move event to date'),{target:{value:'2040-12-20'}});
    fireEvent.click(screen.getByRole('button',{name:'Save event details / move date'}));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByText(/Event details saved and reservation moved to 2040-12-20/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'2040-12-20 — booked locally'})).toHaveClass('booked');
    fireEvent.click(screen.getByRole('button',{name:'2040-12-20 — booked locally'}));
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });
  it('captures the client name when booking and prefills it after reopening',()=>{
    const date=tomorrowLocal();const view=render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Test hall'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Wedding A'}});
    fireEvent.change(screen.getByLabelText('Client name (optional)'),{target:{value:'Demo client'}});
    fireEvent.click(screen.getByRole('button',{name:'Reserve selected date locally'}));
    expect(readBookings()[0].client_name).toBe('Demo client');
    view.unmount();render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    expect(screen.getByLabelText('Client name')).toHaveValue('Demo client');
  });
  it('closes event details from the top without saving edits or changing the reservation',()=>{
    const date=tomorrowLocal();reserveBooking('Hall',date,'Wedding A','Wedding',new Date(),'Original client');
    const original=localStorage.getItem(BOOKING_KEY);
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Client name'),{target:{value:'Unsaved edit'}});
    fireEvent.click(screen.getByRole('button',{name:'Close event details'}));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(localStorage.getItem(BOOKING_KEY)).toBe(original);
    fireEvent.click(screen.getByRole('button',{name:date+' — booked locally'}));
    expect(screen.getByLabelText('Client name')).toHaveValue('Original client');
  });
  it('opens editable event details, persists client information, and moves the booked day',()=>{
    const date=tomorrowLocal();const [b]=reserveBooking('Test hall',date,'Test wedding','Wedding');const change=vi.fn();
    const view=render(<BookingCalendar date={date} eventType="Wedding" onDateChange={change}/>);
    expect(screen.getByLabelText('Client name')).toHaveValue('');
    fireEvent.change(screen.getByLabelText('Client name'),{target:{value:'Demo client'}});
    fireEvent.change(screen.getByLabelText('Client contact (optional)'),{target:{value:'demo@example.invalid'}});
    fireEvent.change(screen.getByLabelText('Booked event type'),{target:{value:'Wedding reception'}});
    fireEvent.change(screen.getByLabelText('Move event to date'),{target:{value:'2040-12-20'}});
    fireEvent.click(screen.getByRole('button',{name:'Save event details / move date'}));
    expect(readBookings()[0]).toMatchObject({id:b.id,date:'2040-12-20',client_name:'Demo client',event_category:'Wedding reception'});
    expect(change).toHaveBeenCalledWith('2040-12-20');
    view.unmount();render(<BookingCalendar date="2040-12-20" eventType="Wedding" onDateChange={change}/>);
    expect(screen.getByLabelText('Client name')).toHaveValue('Demo client');
    expect(screen.getByRole('button',{name:'2040-12-20 — booked locally'})).toHaveClass('booked');
  });
  it('requires confirmation before deleting and frees the date without erasing history',()=>{
    const date=tomorrowLocal();reserveBooking('Hall',date,'A','Wedding');
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Delete reservation'}));
    expect(readBookings()[0].status).toBe('reserved');
    fireEvent.click(screen.getByRole('button',{name:'Keep reservation'}));
    expect(readBookings()[0].status).toBe('reserved');
    fireEvent.click(screen.getByRole('button',{name:'Delete reservation'}));
    fireEvent.click(screen.getByRole('button',{name:'Confirm delete reservation'}));
    expect(readBookings()).toHaveLength(1);expect(readBookings()[0].status).toBe('cancelled');
    expect(screen.getByRole('button',{name:date})).not.toHaveClass('booked');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
  it('reserves with venue, reference and date even when financial setup has no event type',()=>{
    const date=tomorrowLocal();render(<BookingCalendar date={date} eventType="" onDateChange={vi.fn()}/>);
    expect(screen.getByText('Enter a venue / team name.')).toBeInTheDocument();
    expect(screen.getByText('Enter an event reference.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Kingsbury hotel — TEST ONLY'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'birthday party'}});
    expect(screen.queryByText('To reserve this date:')).not.toBeInTheDocument();
    const reserve=screen.getByRole('button',{name:'Reserve selected date locally'});expect(reserve).toBeEnabled();
    fireEvent.click(reserve);
    expect(readBookings()[0]).toMatchObject({label:'birthday party',event_type:'Unspecified',date,status:'reserved'});
    expect(screen.getByText('Date successfully booked!')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(reserve).toBeDisabled();
  });
  it('shows a specific missing-date reason rather than silently disabling reservation',()=>{
    render(<BookingCalendar date="" eventType="" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Birthday'}});
    expect(screen.getByText('Select a future event date on the calendar.')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toHaveAttribute('aria-describedby','booking-requirements');
  });
  it('ignores remembered names and requires manual venue entry in every session',()=>{
    const date=tomorrowLocal();reserveBooking('Hall A',date,'Existing wedding','Wedding');
    rememberCalendar('Hall A');
    const initial=render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Existing wedding');
    expect(screen.getByLabelText('Venue / team calendar')).toHaveAttribute('autocomplete','off');
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall A'}});
    expect(screen.getByRole('alertdialog')).toHaveTextContent('This date is already booked');
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Existing wedding');
    const before=localStorage.getItem(BOOKING_KEY);
    fireEvent.click(screen.getByRole('button',{name:'Review existing event'}));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toBeDisabled();
    expect(localStorage.getItem(BOOKING_KEY)).toBe(before);
    initial.unmount();render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Existing wedding');
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall A'}});
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Existing wedding');
  });
  it('shows saved dates in the calendar without an expanded reservation list or automatic venue selection',()=>{
    const date=tomorrowLocal();reserveBooking('Hall',date,'A','Wedding');const change=vi.fn();
    render(<BookingCalendar date="" eventType="Wedding" onDateChange={change}/>);
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    expect(screen.queryByText(/All upcoming local reservations/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/View reservation:/})).not.toBeInTheDocument();
    expect(screen.getByText('All saved reservations (1 active)').closest('details')).not.toHaveAttribute('open');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:date+' — booked locally'}));
    expect(change).toHaveBeenCalledWith(date);
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    expect(localStorage.getItem(CALENDAR_KEY)).toBeNull();
  });
  it('does not allow a different or blank venue name to bypass a saved date',()=>{
    const date=tomorrowLocal();reserveBooking('Hall A',date,'A','Wedding');
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Wedding: A');
    expect(screen.getByRole('button',{name:date+' — booked locally'})).toHaveClass('booked');
    expect(screen.queryByLabelText('Saved venue / team calendars')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Review existing event'}));
    const venue=screen.getByRole('textbox',{name:'Venue / team calendar'});
    fireEvent.change(venue,{target:{value:'Hall B'}});
    fireEvent.blur(venue);
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Wedding: A');
    expect(localStorage.getItem(CALENDAR_KEY)).toBeNull();
    fireEvent.click(screen.getByRole('button',{name:'Review existing event'}));
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall C'}});
    expect(venue).toHaveValue('Hall C');
    expect(screen.getByRole('alert')).toHaveTextContent('planner already has an event');
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toBeDisabled();
    expect(readBookings()).toHaveLength(1);
  });
  it('chooses a different date without cancelling or modifying the existing booking',()=>{
    const date=tomorrowLocal();reserveBooking('Hall',date,'A','Wedding');const change=vi.fn();
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={change}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    const original=localStorage.getItem(BOOKING_KEY);
    fireEvent.click(screen.getByRole('button',{name:'Choose another date'}));
    expect(change).toHaveBeenCalledWith('');
    expect(localStorage.getItem(BOOKING_KEY)).toBe(original);
  });
  it('offers no past years and clamps past month navigation without changing stored bookings',()=>{
    const current=new Date(),year=current.getFullYear(),month=String(current.getMonth()+1).padStart(2,'0');
    render(<BookingCalendar date={`${year-1}-02-01`} eventType="Wedding" onDateChange={vi.fn()}/>);
    const selector=screen.getByLabelText('Calendar year') as HTMLSelectElement;
    expect(Array.from(selector.options).every(option=>Number(option.value)>=year)).toBe(true);
    expect(selector).toHaveValue(String(year));expect(screen.getByLabelText('Calendar month')).toHaveValue(month);
    expect(screen.getByRole('button',{name:'Previous booking month'})).toBeDisabled();
    fireEvent.change(selector,{target:{value:String(year+1)}});
    fireEvent.change(screen.getByLabelText('Calendar month'),{target:{value:'01'}});
    fireEvent.change(selector,{target:{value:String(year)}});
    expect(screen.getByLabelText('Calendar month')).toHaveValue(month);
    expect(readBookings()).toEqual([]);
  });
  it('jumps directly to a month/year without selecting or reserving a date',()=>{
    const onDateChange=vi.fn();render(<BookingCalendar date="" eventType="Wedding" onDateChange={onDateChange}/>);
    fireEvent.change(screen.getByLabelText('Calendar year'),{target:{value:'2040'}});
    fireEvent.change(screen.getByLabelText('Calendar month'),{target:{value:'12'}});
    expect(screen.getByRole('group',{name:'December 2040 booking dates'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'2040-12-31'})).toBeInTheDocument();
    expect(onDateChange).not.toHaveBeenCalled();expect(readBookings()).toEqual([]);
    fireEvent.click(screen.getByRole('button',{name:'2040-12-31'}));
    expect(onDateChange).toHaveBeenCalledWith('2040-12-31');
  });
  it('keeps arrows and dropdowns synchronized across year boundaries and leap years',()=>{
    render(<BookingCalendar date="2027-12-22" eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Next booking month'}));
    expect(screen.getByLabelText('Calendar year')).toHaveValue('2028');
    expect(screen.getByLabelText('Calendar month')).toHaveValue('01');
    fireEvent.change(screen.getByLabelText('Calendar month'),{target:{value:'02'}});
    expect(screen.getByRole('button',{name:'2028-02-29'})).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Calendar year'),{target:{value:'2027'}});
    expect(screen.queryByRole('button',{name:'2027-02-29'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'2027-02-28'})).toBeInTheDocument();
  });
  it('preserves booked markers after jumping away and back',()=>{
    const date=tomorrowLocal();reserveBooking('Hall',date,'A','Wedding');
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    fireEvent.change(screen.getByLabelText('Calendar year'),{target:{value:'2040'}});
    fireEvent.change(screen.getByLabelText('Calendar year'),{target:{value:date.slice(0,4)}});
    expect(screen.getByRole('button',{name:date+' — booked locally'})).toHaveClass('booked');
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toBeDisabled();
  });
  it('starts with unknown external availability and never reserves just by selecting a date',()=>{
    const onDateChange=vi.fn();const date=tomorrowLocal();
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={onDateChange}/>);
    expect(screen.getByText('Enter a venue / team name.')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:date}));expect(onDateChange).toHaveBeenCalledWith(date);
    expect(readBookings()).toEqual([]);
  });
  it('reserves explicitly, blocks duplicates and shows red booked calendar day',()=>{
    const date=tomorrowLocal();render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall A'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Wedding A'}});
    fireEvent.click(screen.getByRole('button',{name:'Reserve selected date locally'}));
    expect(screen.getByText('Date successfully booked!')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.queryByText('To reserve this date:')).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toBeDisabled();
    expect(screen.getByRole('button',{name:date+' — booked locally'})).toHaveClass('booked');
    expect(readBookings()).toHaveLength(1);
    cleanup();render(<BookingCalendar date={date} eventType="Corporate" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'hall a'}});
    expect(screen.getByRole('alert')).toHaveTextContent('Wedding A');
  });
  it('shows a conflict only on reselecting a saved date, without creating another record',()=>{
    const date=tomorrowLocal();render(<BookingCalendar date={date} eventType="" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Birthday'}});
    fireEvent.click(screen.getByRole('button',{name:'Reserve selected date locally'}));
    expect(screen.getByText('Date successfully booked!')).toBeInTheDocument();
    const saved=localStorage.getItem(BOOKING_KEY);
    fireEvent.click(screen.getByRole('button',{name:date+' — booked locally'}));
    expect(screen.queryByText('Date successfully booked!')).not.toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Already booked locally');
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Birthday');
    expect(localStorage.getItem(BOOKING_KEY)).toBe(saved);
    expect(readBookings()).toHaveLength(1);
  });
  it('restores saved markers and upcoming records on reopening without a stale success message',()=>{
    const date=tomorrowLocal();const first=render(<BookingCalendar date={date} eventType="" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Birthday'}});
    fireEvent.click(screen.getByRole('button',{name:'Reserve selected date locally'}));first.unmount();
    render(<BookingCalendar date="" eventType="" onDateChange={vi.fn()}/>);
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    expect(screen.getByRole('button',{name:date+' — booked locally'})).toHaveClass('booked');
    expect(screen.queryByText(/All upcoming local reservations/)).not.toBeInTheDocument();
    expect(readBookings()).toHaveLength(1);
    expect(screen.queryByText('Date successfully booked!')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
  it('preserves legacy same-day records behind collapsed management and marks their date red without a large warning',()=>{
    const date=tomorrowLocal();const [a]=reserveBooking('Hall A',date,'First','Wedding');
    const b={...a,id:'legacy-second',resource:'Hall B',label:'Second'};
    const original=JSON.stringify({version:1,bookings:[a,b]});localStorage.setItem(BOOKING_KEY,original);
    render(<BookingCalendar date="" eventType="" onDateChange={vi.fn()}/>);
    expect(screen.queryByText('Existing duplicate dates need review.')).not.toBeInTheDocument();
    expect(screen.getByText('Booked (2)')).toBeInTheDocument();
    expect(screen.queryByText(/All upcoming local reservations/)).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:date+' — booked locally'})).toHaveClass('booked');
    expect(screen.getByRole('button',{name:date+' — booked locally'})).toHaveAttribute('title','Hall A: First; Hall B: Second');
    expect(screen.getByText('All saved reservations (2 active)').closest('details')).not.toHaveAttribute('open');
    expect(localStorage.getItem(BOOKING_KEY)).toBe(original);
    expect(()=>reserveBooking('Hall C',date,'Third')).toThrow(/Already booked/);
    fireEvent.click(screen.getAllByRole('button',{name:'Cancel reservation'})[0]);
    expect(screen.queryByText('Existing duplicate dates need review.')).not.toBeInTheDocument();
    expect(readBookings()).toHaveLength(2);
    expect(()=>changeBooking(a.id,'reserved')).toThrow(/another event/);
  });
  it('rechecks stored dates at reservation time even when the UI has not seen another write',()=>{
    const date=tomorrowLocal();render(<BookingCalendar date={date} eventType="" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall B'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Second'}});
    reserveBooking('Hall A',date,'First');const original=localStorage.getItem(BOOKING_KEY);
    fireEvent.click(screen.getByRole('button',{name:'Reserve selected date locally'}));
    expect(screen.queryByText('Date successfully booked!')).not.toBeInTheDocument();
    expect(screen.getByRole('alertdialog')).toHaveTextContent('First');
    expect(localStorage.getItem(BOOKING_KEY)).toBe(original);
    expect(readBookings()).toHaveLength(1);
  });
  it('does not display a success when storage rejects a reservation',()=>{
    render(<BookingCalendar date={tomorrowLocal()} eventType="" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    fireEvent.change(screen.getByLabelText('Event reference'),{target:{value:'Birthday'}});
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('storage unavailable');});
    fireEvent.click(screen.getByRole('button',{name:'Reserve selected date locally'}));
    expect(screen.queryByText('Date successfully booked!')).not.toBeInTheDocument();
    expect(screen.getByText('storage unavailable')).toBeInTheDocument();expect(readBookings()).toEqual([]);
  });
  it('responds to cancellation and other-tab storage events',()=>{
    const date=tomorrowLocal();const [b]=reserveBooking('Hall',date,'A','Wedding');
    render(<BookingCalendar date={date} eventType="Wedding" onDateChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Hall'}});
    expect(screen.getByRole('alert')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Cancel reservation'}));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    changeBooking(b.id,'reserved');fireEvent(window,new StorageEvent('storage',{key:BOOKING_KEY}));
    expect(screen.getByRole('alert')).toHaveTextContent('Already booked');
  });
  it('fails closed on corrupt register rather than showing availability',()=>{
    localStorage.setItem(BOOKING_KEY,'bad');render(<BookingCalendar date={tomorrowLocal()} eventType="Wedding" onDateChange={vi.fn()}/>);
    expect(screen.getByRole('alert')).toHaveTextContent('Availability is unknown');
    expect(screen.getByRole('button',{name:'Reserve selected date locally'})).toBeDisabled();
    expect(localStorage.getItem(BOOKING_KEY)).toBe('bad');
  });
});
