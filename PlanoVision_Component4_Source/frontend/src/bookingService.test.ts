import {afterEach,describe,it,expect,vi} from 'vitest';
import {bookingService} from './bookingService';
import {BOOKING_KEY} from './bookingRegister';
const b={id:'test-id',resource:'TEST hall',date:'2040-11-05',label:'TEST wedding',event_type:'Wedding',status:'reserved',created_at:'2026-10-20T00:00:00Z',client_name:'TEST client'} as const;
afterEach(()=>{localStorage.clear();vi.unstubAllGlobals();});
const response=(rows:unknown[]=[b],revision=1)=>({ok:true,json:async()=>({storage:'sqlite',records:rows,revisions:{'test-id':revision}})});
describe('Real booking HTTP adapter',()=>{
  it('uses backend list, create, update, cancellation and restore with revisions',async()=>{
    const f=vi.fn().mockResolvedValueOnce(response()).mockResolvedValueOnce(response()).mockResolvedValueOnce(response([b],2)).mockResolvedValueOnce(response([{...b,status:'cancelled'}],3)).mockResolvedValueOnce(response([b],4));vi.stubGlobal('fetch',f);
    const rows=await bookingService.read();expect(rows).toEqual([{...b,revision:1}]);
    await bookingService.reserve('TEST hall','2040-11-05','TEST wedding','Wedding','TEST client');
    expect(JSON.parse(f.mock.calls[1][1].body).record.client_name).toBe('TEST client');
    const updated=await bookingService.update(rows[0],{date:'2040-11-06',label:'changed'});
    expect(JSON.parse(f.mock.calls[2][1].body).expected_revision).toBe(1);
    const cancelled=await bookingService.status(updated[0],'cancelled');expect(f.mock.calls[3][1].method).toBe('DELETE');
    await bookingService.status(cancelled[0],'reserved');expect(JSON.parse(f.mock.calls[4][1].body).expected_revision).toBe(3);
    expect(localStorage.getItem(BOOKING_KEY)).toBeNull();
  });
  it('rejects backend failures and malformed data without local fallback',async()=>{
    localStorage.setItem(BOOKING_KEY,JSON.stringify({version:1,bookings:[b]}));
    const f=vi.fn().mockRejectedValueOnce(Error('offline')).mockResolvedValueOnce({ok:true,json:async()=>({records:[b]})});vi.stubGlobal('fetch',f);
    await expect(bookingService.read()).rejects.toThrow('offline');
    await expect(bookingService.read()).rejects.toThrow('Invalid backend');
  });
});
