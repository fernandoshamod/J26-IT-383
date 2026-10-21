import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import ServerPlans from './ServerPlans';
import {defaults} from './api';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const saved={id:'record-1',name:'Wedding A',client_name:'TEST client',plan:defaults,created_at:'2026-10-20T00:00:00Z',updated_at:'2026-10-20T00:00:00Z'};
const reply=(records:unknown[]=[],revision=1)=>({ok:true,json:async()=>({storage:'sqlite',records,revisions:{'record-1':revision}})});
describe('Backend financial event controls',()=>{
  it('saves original inputs, lists after refresh, loads, updates and confirms deletion',async()=>{
    const fetcher=vi.fn().mockResolvedValueOnce(reply([])).mockResolvedValueOnce(reply([saved])).mockResolvedValueOnce(reply([saved])).mockResolvedValueOnce(reply([saved],2)).mockResolvedValueOnce(reply([]));
    vi.stubGlobal('fetch',fetcher);const load=vi.fn();
    render(<ServerPlans plan={defaults} ready onLoad={load}/>);
    await screen.findByText('No saved backend events yet.');
    fireEvent.change(screen.getByLabelText('Saved event name'),{target:{value:'Wedding A'}});
    fireEvent.change(screen.getByLabelText('Saved event client name'),{target:{value:'TEST client'}});
    fireEvent.click(screen.getByRole('button',{name:'Save new event to backend'}));
    await screen.findByText(/Financial event saved in backend SQLite/);
    expect(JSON.parse(fetcher.mock.calls[1][1].body).record).toEqual({name:'Wedding A',client_name:'TEST client',plan:defaults});
    fireEvent.click(screen.getByRole('button',{name:'Refresh backend events'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh backend events'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:/Wedding A/}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Load saved event'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Load saved event'}));expect(load).toHaveBeenCalledWith(defaults);
    fireEvent.click(screen.getByRole('button',{name:'Update selected backend event'}));
    await waitFor(()=>expect(fetcher).toHaveBeenCalledWith('/api/planner/events/record-1',expect.objectContaining({method:'PUT'})));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Delete saved event'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Delete saved event'}));
    expect(fetcher).toHaveBeenCalledTimes(4);
    fireEvent.click(screen.getByRole('button',{name:'Confirm delete saved event'}));
    await screen.findByText('Saved financial event deleted from the active list.');
    expect(JSON.parse(fetcher.mock.calls[4][1].body)).toEqual({expected_revision:2});
  });
  it('does not claim save success or fall back to browser storage when backend fails',async()=>{
    const spy=vi.spyOn(Storage.prototype,'setItem');
    vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(reply([])).mockResolvedValue({ok:false,json:async()=>({error:'Database unavailable'})}));
    render(<ServerPlans plan={defaults} ready onLoad={vi.fn()}/>);
    await screen.findByText('No saved backend events yet.');
    fireEvent.change(screen.getByLabelText('Saved event name'),{target:{value:'A'}});
    fireEvent.click(screen.getByRole('button',{name:'Save new event to backend'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable');
    expect(screen.queryByText(/Financial event saved in backend SQLite/)).not.toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();spy.mockRestore();
  });
  it('disables saves for uncalculated inputs',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply([])));
    render(<ServerPlans plan={defaults} ready={false} onLoad={vi.fn()}/>);
    await screen.findByText('No saved backend events yet.');
    fireEvent.change(screen.getByLabelText('Saved event name'),{target:{value:'A'}});
    expect(screen.getByRole('button',{name:'Save new event to backend'})).toBeDisabled();
  });
  it('automatically lists saved events without loading values into the blank form',async()=>{
    const f=vi.fn().mockResolvedValue(reply([saved]));vi.stubGlobal('fetch',f);const load=vi.fn();
    render(<ServerPlans plan={defaults} ready onLoad={load}/>);
    const row=await screen.findByRole('button',{name:/Wedding A/});expect(f).toHaveBeenCalledTimes(1);expect(load).not.toHaveBeenCalled();
    fireEvent.click(row);
    expect(screen.getByRole('button',{name:'Update selected backend event'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Load saved event'}));
    expect(load).toHaveBeenCalledWith(defaults);expect(screen.getByRole('button',{name:'Update selected backend event'})).toBeEnabled();
  });
  it('does not silently adopt a newer revision when refreshing a loaded event',async()=>{
    const f=vi.fn().mockResolvedValueOnce(reply([saved])).mockResolvedValueOnce(reply([saved],2)).mockResolvedValueOnce({ok:false,json:async()=>({error:'Record changed in another session. Reload before editing.'})});vi.stubGlobal('fetch',f);
    render(<ServerPlans plan={defaults} ready onLoad={vi.fn()}/>);
    fireEvent.click(await screen.findByRole('button',{name:/Wedding A/}));fireEvent.click(screen.getByRole('button',{name:'Load saved event'}));
    fireEvent.click(screen.getByRole('button',{name:'Refresh backend events'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Refresh backend events'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Update selected backend event'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('another session');expect(JSON.parse(f.mock.calls[2][1].body).expected_revision).toBe(1);
  });
  it('shows automatic read failures and offers refresh rather than fabricating an empty list',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(Error('Offline')));render(<ServerPlans plan={defaults} ready onLoad={vi.fn()}/>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Offline');expect(screen.queryByText('No saved backend events yet.')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'Refresh backend events'})).toBeEnabled();
  });
  it('keeps large event libraries searchable and paginated',async()=>{
    const records=Array.from({length:7},(_,i)=>({...saved,id:`record-${i+1}`,name:`Event ${i+1}`,client_name:`Client ${i+1}`}));
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({storage:'sqlite',records,revisions:Object.fromEntries(records.map(r=>[r.id,1]))})}));
    render(<ServerPlans plan={defaults} ready onLoad={vi.fn()}/>);
    await screen.findByRole('button',{name:/Event 1/});
    expect(screen.queryByRole('button',{name:/Event 6/})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Next →'}));
    expect(screen.getByRole('button',{name:/Event 6/})).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Search saved events'),{target:{value:'Client 3'}});
    expect(screen.getByRole('button',{name:/Event 3/})).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Event 6/})).not.toBeInTheDocument();
  });
});
