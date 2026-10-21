import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import App from './App';
import {defaults,type Inputs,type Comparison} from './api';
import {PLAN_KEY,serializePlan} from './planStorage';

// TEST ONLY: in-memory HTTP responses exercise real page/control wiring, not model accuracy.
type Row={id:string;name:string;client_name:string;plan:Inputs;created_at:string;updated_at:string};
let rows:Row[],revision:number,writes:string[];
const initial:Inputs={...defaults,event_date:'2040-12-20'};
const listing=()=>({storage:'sqlite',records:structuredClone(rows),revisions:Object.fromEntries(rows.map(r=>[r.id,revision]))});
function comparison(base:Inputs,alt:Inputs):Comparison{
  const result=(p:Inputs)=>{
    const extras=p.quotes.filter(q=>!p.removed_quote_ids.includes(q.id)).reduce((sum,q)=>sum+(q.unit_rate_lkr??0),0);
    const cost=1570450.2+extras,profit=p.retained_receipts_lkr-cost;
    return {status:'calculated',blockers:[],plan:{total_cost_lkr:cost,expected_profit_lkr:profit,expected_margin_pct:profit/p.retained_receipts_lkr*100,reserve_lkr:cost*.1,budget_headroom_lkr:p.target_budget_lkr-cost,retained_receipts_lkr:p.retained_receipts_lkr,recommended_client_price_excluding_output_tax_lkr:cost*1.1/.85,budget_feasible:cost<=p.target_budget_lkr,affordable_after_reserve:cost*1.1<=p.target_budget_lkr,margin_feasible:profit/p.retained_receipts_lkr*100>=p.min_profit_margin_pct,space_utilization:.618,used_area_m2:309,seats:p.guests,tables:25,staff:7,line_items_lkr:{catering:1570450.2,...Object.fromEntries(p.quotes.filter(q=>!p.removed_quote_ids.includes(q.id)).map(q=>['extra:'+q.id,q.unit_rate_lkr??0]))},warnings:[]},model_scores:{Budget_Overrun:null,Profit_Margin_Risk:null},geometry:{venue_area_m2:500,area_rule_capacity:277,guests_per_m2:.3},monte_carlo:{overrun_frequency:.1,margin_risk_frequency:.1,cost_lkr:{mean:cost,p05:cost*.9,p95:cost*1.1}},draft_planning_health:{score_points:100}};
  };
  const baseline=result(base),alternative=result(alt);
  return {api_version:'lkr-dashboard.0.1',mode:'research_only',baseline,alternative,delta:{cost_lkr:alternative.plan.total_cost_lkr-baseline.plan.total_cost_lkr,profit_lkr:alternative.plan.expected_profit_lkr-baseline.plan.expected_profit_lkr,margin_pct_points:alternative.plan.expected_margin_pct-baseline.plan.expected_margin_pct,line_changes_lkr:{}},report_text:`TEST ONLY REPORT: cost ${alternative.plan.total_cost_lkr}`,insights:{status:'calculated',score:{name:'TEST ONLY',value:100,status:'within_modelled_rules',formula:'TEST ONLY',budget_coverage:1,margin_coverage:1,budget_formula:'TEST ONLY',margin_formula:'TEST ONLY',limitation:'Test fixture, not model evidence'},recommendations:[],explainability:{method:'ledger_delta_only',drivers:[]}},provenance:{configuration_sha256:'TEST ONLY',model_run:'TEST ONLY',live_vendor_fetch:false}};
}
beforeEach(()=>{
  localStorage.clear();localStorage.setItem(PLAN_KEY,serializePlan(initial));history.replaceState(null,'','/');revision=1;writes=[];
  rows=[{id:'event-a',name:'Backend wedding',client_name:'TEST client',plan:structuredClone(initial),created_at:'2026-10-20',updated_at:'2026-10-20'}];
  vi.stubGlobal('fetch',vi.fn(async(url,options)=>{
    const path=String(url),method=options?.method??'GET',body=options?.body?JSON.parse(options.body as string):null;
    let value:unknown;
    if(path==='/api/planner/events'&&method==='GET')value=listing();
    else if(path==='/api/planner/bookings')value={storage:'sqlite',records:[],revisions:{}};
    else if(path==='/api/planner/compare')value=comparison(body.baseline,body.alternative);
    else if(path.startsWith('/api/planner/events/')){
      writes.push(method);const id=path.split('/').at(-1);
      if(body.expected_revision!==revision)return {ok:false,json:async()=>({error:'Revision conflict'})};
      if(method==='DELETE')rows=rows.filter(r=>r.id!==id);
      else rows=rows.map(r=>r.id===id?{...r,...structuredClone(body.record)}:r);
      revision++;value=listing();
    }else return {ok:false,json:async()=>({error:'Optional endpoint unavailable in TEST ONLY fixture'})};
    return {ok:true,json:async()=>value};
  }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
async function loadEvent(){
  await screen.findByText('Estimated event cost');
  fireEvent.click(screen.getByRole('link',{name:'Saved events'}));
  fireEvent.click(await screen.findByRole('button',{name:/Backend wedding/}));
  fireEvent.click(screen.getByRole('button',{name:'Load saved event'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Update selected backend event'})).toBeEnabled());
}
describe('Connected Planner → What-If → Reports → SQLite controls',()=>{
  it('retains identity across pages, previews without writes, confirms then explicitly saves to the same record',async()=>{
    render(<App/>);await loadEvent();
    fireEvent.click(screen.getByRole('link',{name:'Financial planner'}));
    fireEvent.click(screen.getByRole('button',{name:'Use original plan for client changes'}));
    fireEvent.change(screen.getByLabelText('Expense name'),{target:{value:'Fireworks'}});fireEvent.change(screen.getByLabelText('Estimated total amount (LKR)'),{target:{value:'50000'}});fireEvent.click(screen.getByRole('button',{name:'Preview addition'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm changes to main plan'})).toBeEnabled());
    expect(writes).toEqual([]);expect(rows[0].plan.quotes).toHaveLength(0);
    fireEvent.click(screen.getByRole('link',{name:/Reports & explainability/}));
    fireEvent.click(screen.getByRole('button',{name:'Generate explainable report'}));expect(screen.getByLabelText('Generated report')).toHaveTextContent('1620450.2');
    expect(screen.getByText(/Report scope: unconfirmed expense preview/)).toBeInTheDocument();expect(writes).toEqual([]);
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));fireEvent.click(screen.getByRole('button',{name:'Confirm changes to main plan'}));
    expect(writes).toEqual([]);expect(rows[0].plan.quotes).toHaveLength(0);
    fireEvent.click(screen.getByRole('button',{name:'Save confirmed plan to backend →'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Update selected backend event'})).toBeEnabled());
    expect(screen.getByRole('button',{name:/Backend wedding/})).toHaveAttribute('aria-pressed','true');expect(screen.getByLabelText('Saved event client name')).toHaveValue('TEST client');
    fireEvent.click(screen.getByRole('button',{name:'Update selected backend event'}));await screen.findByText(/Financial event saved in backend SQLite/);
    expect(writes).toEqual(['PUT']);expect(rows).toHaveLength(1);expect(rows[0].plan.quotes).toHaveLength(1);expect(rows[0].plan.quotes[0].unit_rate_lkr).toBe(50000);
  });
  it('clears the backend update identity for a new blank event, without deleting saved events',async()=>{
    render(<App/>);await loadEvent();fireEvent.click(screen.getByRole('link',{name:'Financial planner'}));fireEvent.click(screen.getByRole('button',{name:'New blank event'}));fireEvent.click(screen.getByRole('link',{name:'Saved events'}));
    const row=await screen.findByRole('button',{name:/Backend wedding/});
    expect(row).toHaveAttribute('aria-pressed','false');expect(screen.getByLabelText('Saved event name')).toHaveValue('');expect(screen.queryByRole('button',{name:'Update selected backend event'})).not.toBeInTheDocument();expect(rows).toHaveLength(1);expect(writes).toEqual([]);
  });
  it('keeps deletion behind confirmation and never turns financial deletion into a calendar cancellation',async()=>{
    render(<App/>);await loadEvent();fireEvent.click(screen.getByRole('button',{name:'Delete saved event'}));expect(writes).toEqual([]);
    fireEvent.click(screen.getByRole('button',{name:'Keep saved event'}));expect(rows).toHaveLength(1);
    fireEvent.click(screen.getByRole('button',{name:'Delete saved event'}));fireEvent.click(screen.getByRole('button',{name:'Confirm delete saved event'}));await screen.findByText('Saved financial event deleted from the active list.');expect(writes).toEqual(['DELETE']);expect(rows).toHaveLength(0);
    expect(vi.mocked(fetch).mock.calls.some(([url,o])=>String(url).startsWith('/api/planner/bookings')&&o?.method==='DELETE')).toBe(false);
  });
});
