import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {defaults,decode} from './api';
import {PLAN_KEY,serializePlan,parsePlan,restorePlan,savePlan} from './planStorage';
import PlanFiles from './PlanFiles';
import PricingScope from './PricingScope';
import response from './test-fixtures/training-evaluation.response.json';
beforeEach(()=>localStorage.clear());afterEach(()=>{cleanup();vi.restoreAllMocks();});
describe('Main-plan persistence',()=>{
  it('round trips only inputs, never predictions or draft outcomes',()=>{
    const text=serializePlan(defaults);expect(parsePlan(text)).toEqual(defaults);
    expect(Object.keys(JSON.parse(text))).toEqual(['format','saved_at','plan']);
    expect(savePlan(defaults)).toContain('saved');expect(restorePlan().plan).toEqual(defaults);
  });
  it('rejects incompatible, injected and invalid files',()=>{
    for(const plan of [{...defaults,model_scores:{}},{...defaults,guests:'150'},{...defaults,event_date:'2026-02-30'},{...defaults,removed_quote_ids:['unknown']}]){
      const text=JSON.stringify({format:PLAN_KEY,saved_at:'2026-10-18T00:00:00Z',plan});expect(()=>parsePlan(text)).toThrow();
    }
    expect(()=>parsePlan('x'.repeat(131073))).toThrow();expect(()=>parsePlan('{}')).toThrow();
  });
  it('preserves unreadable storage without silently overwriting it',()=>{
    localStorage.setItem(PLAN_KEY,'bad data');expect(restorePlan().plan).toBeNull();
    expect(localStorage.getItem(PLAN_KEY)).toBe('bad data');
    expect(restorePlan().message).toContain('not overwritten');
  });
  it('warns when browser storage is unavailable',()=>{
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota');});
    expect(savePlan(defaults)).toContain('storage failed');
  });
  it('imports a portable input backup without trusting computed results',async()=>{
    const onLoad=vi.fn();render(<PlanFiles plan={defaults} ready={true} onLoad={onLoad}/>);
    fireEvent.change(screen.getByLabelText('Restore an exported PlanoVision plan'),{target:{files:[{size:100,text:async()=>serializePlan({...defaults,guests:160})}]}});
    await waitFor(()=>expect(onLoad).toHaveBeenCalledWith({...defaults,guests:160}));
    expect(localStorage.getItem(PLAN_KEY)).toBeNull();
    fireEvent.change(screen.getByLabelText('Restore an exported PlanoVision plan'),{target:{files:[{size:2,text:async()=>'{}'}]}});
    expect(await screen.findByText(/Import rejected/)).toBeInTheDocument();expect(onLoad).toHaveBeenCalledTimes(1);
  });
});
describe('Price scope',()=>{
  it('does not imply a future forecast when evidence is unavailable',()=>{
    render(<PricingScope data={decode(response)}/>);expect(screen.getByText(/No calibrated event-date price forecast/)).toBeInTheDocument();
  });
  it('rejects claims of independently verified prices from the response',()=>{
    expect(()=>decode({...response,pricing_scope:{baseline:{},alternative:{}}})).toThrow('Invalid price-scope evidence');
  });
});
