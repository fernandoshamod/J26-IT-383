import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import ScoreBar,{scoreBand} from './ScoreBar';
import App from './App';
import ModelEvidence from './ModelEvidence';
import {decode,defaults,validateInputs,type Comparison} from './api';
import {PLAN_KEY,serializePlan,parsePlan} from './planStorage';
import {blankEvent,tomorrowLocal,validateEventSetup} from './eventSetup';

// TEST ONLY isolate calculation tests from the independent booking HTTP adapter.
// bookingService.test and backend tests exercise real persistence request semantics.
vi.mock('./bookingService',()=>({bookingService:{read:()=>[],reserve:vi.fn(),update:vi.fn(),status:vi.fn(),importLegacy:vi.fn()}}));
// Calculation-only tests isolate persistence. AppPersistence.test exercises the real controls together.
vi.mock('./ServerPlans',()=>({default:()=>null,blankBackendSession:()=>({name:'',client:'',selected:'',loaded:'',loadedRevision:0})}));

// TEST ONLY: rendered API fixtures, never supplied as live/planner rate evidence.
function fixture():Comparison{
  const result={status:'calculated',plan:{total_cost_lkr:1570450.2,expected_profit_lkr:929549.8,expected_margin_pct:37.18,reserve_lkr:157045,budget_headroom_lkr:429549.8,retained_receipts_lkr:2500000,recommended_client_price_excluding_output_tax_lkr:2032347,budget_feasible:true,affordable_after_reserve:true,margin_feasible:true,space_utilization:.618,used_area_m2:309,seats:150,tables:25,staff:7,line_items_lkr:{catering:1570450.2},warnings:[]},blockers:[],model_scores:{Budget_Overrun:null,Profit_Margin_Risk:null},geometry:{venue_area_m2:500,area_rule_capacity:277,guests_per_m2:.3},monte_carlo:{overrun_frequency:.1,margin_risk_frequency:.2,cost_lkr:{p05:1400000,p95:1700000,mean:1570450}},draft_planning_health:{score_points:100}};
  return {api_version:'lkr-dashboard.0.1',mode:'research_only',baseline:structuredClone(result),alternative:structuredClone(result),delta:{cost_lkr:0,profit_lkr:0,margin_pct_points:0,line_changes_lkr:{}},report_text:'TEST ONLY',insights:{status:'calculated',score:{name:'Experimental planning coverage',value:100,status:'within_modelled_rules',formula:'100 × min(budget_coverage, margin_coverage)',budget_coverage:1,margin_coverage:1,budget_formula:'TEST ONLY',margin_formula:'TEST ONLY',limitation:'Not validated'},recommendations:[],explainability:{method:'ledger_delta_only',drivers:[]}},provenance:{configuration_sha256:'test-only-not-a-real-hash',model_run:'test-fixture',live_vendor_fetch:false}};
}
beforeEach(()=>{localStorage.clear();localStorage.setItem(PLAN_KEY,serializePlan(defaults));history.replaceState(null,'','/');vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>fixture()})));});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('Planner dashboard',()=>{
  it('opens a fresh event with no prefilled details or automatic model call',async()=>{
    localStorage.clear();render(<App/>);
    expect(screen.getByLabelText('Event type')).toHaveValue('');
    expect(screen.getByLabelText(/Event date/)).toHaveValue('');
    expect(screen.getByLabelText(/Event date/)).toHaveAttribute('min',tomorrowLocal());
    for(const title of ['Guest count','Event duration','Venue width','Venue length','Maximum allowed spending','Expected client payment','Minimum profit margin'])expect(screen.getByLabelText(title)).toHaveValue(null);
    expect(screen.getByText('Enter your event to begin')).toBeInTheDocument();
    await new Promise(resolve=>setTimeout(resolve,400));expect(fetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('link',{name:'Saved events'}));
    expect(screen.getByRole('button',{name:'Save main plan in this browser'})).toBeDisabled();
    expect(screen.queryByText('Estimated event cost')).not.toBeInTheDocument();
  });
  it('uses local tomorrow and rejects today, past dates and missing event type',()=>{
    const now=new Date(2026,9,22,23,59);
    expect(tomorrowLocal(now)).toBe('2026-10-23');
    expect(tomorrowLocal(new Date(2026,11,31))).toBe('2027-01-01');
    expect(validateEventSetup({...defaults,event_date:'2026-10-22'},now)).toMatch(/future/);
    expect(validateEventSetup({...defaults,event_date:'2026-10-21'},now)).toMatch(/future/);
    expect(validateEventSetup({...defaults,event_date:'2026-10-23'},now)).toBeNull();
    expect(validateEventSetup({...defaults,event_type:'',event_date:'2026-10-23'},now)).toMatch(/event type/);
    expect(validateEventSetup(blankEvent(),now)).not.toBeNull();
  });
  it('calculates a user-entered new event only when all fields are complete',async()=>{
    localStorage.clear();render(<App/>);
    fireEvent.change(screen.getByLabelText('Event type'),{target:{value:'Corporate'}});
    fireEvent.change(screen.getByLabelText(/Event date/),{target:{value:tomorrowLocal()}});
    for(const [title,value] of [['Guest count','120'],['Event duration','6'],['Venue width','22'],['Venue length','26'],['Maximum allowed spending','2100000'],['Expected client payment','2600000']])fireEvent.change(screen.getByLabelText(title),{target:{value}});
    await new Promise(resolve=>setTimeout(resolve,400));expect(fetch).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('Minimum profit margin'),{target:{value:'18'}});
    await screen.findByText('Estimated event cost');
    const body=JSON.parse(vi.mocked(fetch).mock.calls.find(([,o])=>!!o?.body)![1]!.body as string);
    expect(body.baseline).toEqual(body.alternative);
    expect(body.baseline).toMatchObject({event_type:'Corporate',event_date:tomorrowLocal(),guests:120,event_hours:6,venue_width_m:22,venue_length_m:26,target_budget_lkr:2100000,retained_receipts_lkr:2600000,min_profit_margin_pct:18});
  });
  it('clears the editor for a new event without deleting a saved plan or leaving stale results',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:'Booking calendar'}));
    fireEvent.change(screen.getByLabelText('Venue / team calendar'),{target:{value:'Previous venue'}});
    fireEvent.click(screen.getByRole('link',{name:'Financial planner'}));
    const saved=localStorage.getItem(PLAN_KEY);
    fireEvent.click(screen.getByRole('button',{name:'New blank event'}));
    expect(screen.getByLabelText('Guest count')).toHaveValue(null);
    expect(screen.getByLabelText('Event type')).toHaveValue('');
    expect(screen.queryByText('Estimated event cost')).not.toBeInTheDocument();
    expect(localStorage.getItem(PLAN_KEY)).toBe(saved);
    fireEvent.click(screen.getByRole('link',{name:'Booking calendar'}));
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    fireEvent.click(screen.getByRole('link',{name:'Saved events'}));
    expect(screen.getByRole('button',{name:'Save main plan in this browser'})).toBeDisabled();
  });
  it('restores saved main inputs and recalculates rather than loading old results',async()=>{
    localStorage.setItem(PLAN_KEY,serializePlan({...defaults,guests:160}));render(<App/>);
    expect(screen.getByLabelText('Guest count')).toHaveValue(160);
    expect(screen.getByText(/Saved main plan restored/)).toBeInTheDocument();
    await screen.findByText('Estimated event cost');
    const call=vi.mocked(fetch).mock.calls.find(([,options])=>!!options?.body)!;
    const request=JSON.parse(call[1]!.body as string);expect(request.baseline.guests).toBe(160);expect(request.alternative.guests).toBe(160);
  });
  it('saves the baseline without saving an unconfirmed client expense',async()=>{
    const first=render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:'Saved events'}));
    fireEvent.click(screen.getByRole('button',{name:'Save main plan in this browser'}));
    fireEvent.click(screen.getByRole('link',{name:'Financial planner'}));
    fireEvent.click(screen.getByRole('button',{name:'Use original plan for client changes'}));
    fireEvent.change(screen.getByLabelText('Expense name'),{target:{value:'Fireworks'}});
    fireEvent.change(screen.getByLabelText('Estimated total amount (LKR)'),{target:{value:'50000'}});
    fireEvent.click(screen.getByRole('button',{name:'Preview addition'}));
    expect(parsePlan(localStorage.getItem(PLAN_KEY)! ).quotes).toHaveLength(0);
    first.unmount();history.replaceState(null,'','/');render(<App/>);
    await screen.findByText('Estimated event cost');expect(screen.getByLabelText('Guest count')).toHaveValue(150);
    expect(parsePlan(localStorage.getItem(PLAN_KEY)!).quotes).toHaveLength(0);
  });
  it('opens supplier terms only on request and submits declared escalation without inventing taxes',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    fireEvent.click(screen.getByText('Supplier quotation terms (optional)'));
    const id=await screen.findByLabelText('Service identifier');fireEvent.change(id,{target:{value:'photography'}});
    fireEvent.change(screen.getByLabelText('Service label'),{target:{value:'Supplied photography'}});
    fireEvent.change(screen.getByLabelText('Unit price (LKR; blank = unknown)'),{target:{value:'10000'}});
    fireEvent.change(screen.getByLabelText('Quote/source reference'),{target:{value:'TEST ONLY reference'}});
    fireEvent.change(screen.getByLabelText('Charge scope'),{target:{value:'exclusive_declared'}});
    expect(screen.getByLabelText('Tax %')).toHaveValue(null);
    fireEvent.change(screen.getByLabelText('Service charge %'),{target:{value:'10'}});
    fireEvent.change(screen.getByLabelText('Tax %'),{target:{value:'18'}});
    fireEvent.change(screen.getByLabelText('Future price terms'),{target:{value:'documented_escalation'}});
    fireEvent.change(screen.getByLabelText('Total documented increase to event date (%)'),{target:{value:'10'}});
    fireEvent.click(screen.getByRole('button',{name:'Add supplied quotation'}));
    await waitFor(()=>{
      const call=vi.mocked(fetch).mock.calls.filter(([,o])=>!!o?.body).at(-1)!;
      const q=JSON.parse(call[1]!.body as string).alternative.quotes[0];
      expect(q).toMatchObject({tax_pct:18,service_pct:10,increase_pct:10,pricing_policy:'documented_escalation',source_kind:'user_supplied_unverified_quote'});
    });
  });
  function modelFixture():Comparison{
    const r=fixture();r.alternative.model_scores={Budget_Overrun:{uncalibrated_score:.67,class:1}};
    r.baseline.model_scores={Budget_Overrun:{uncalibrated_score:.001,class:0}};
    r.alternative.model_trace={run_id:'TEST-ONLY-v3-native',method:'native_xgboost_saved_model_predict',prediction_executed:true,training_rows:2160,test_rows:720,independent_root_families:600,feature_count:1,input_features:{Optional_Expense_Total_LKR:500000},model_sha256:{Budget_Overrun:'a'.repeat(64)},design_sha256:'b'.repeat(64),support_reasons:[],test_metrics:{Budget_Overrun:{xgboost:{accuracy:.95,roc_auc:.99},planning_rule_class_accuracy:.955555}},limitations:['TEST ONLY: no observed event validation'],shap_additivity_verified:true};return r;
  }
  it('shows native model identity, actual input exposure and honest rule comparison',()=>{
    const r=modelFixture();expect(decode(r)).toBe(r);render(<ModelEvidence data={r}/>);
    expect(screen.getByText('Native XGBoost prediction executed')).toBeInTheDocument();
    expect(screen.getByText('0.0010 → 0.6700')).toBeInTheDocument();
    expect(screen.getByText('Optional_Expense_Total_LKR')).toBeInTheDocument();
    expect(screen.getByText('95.56%')).toBeInTheDocument();
    expect(screen.getByText(/does not demonstrate a classification-accuracy advantage/)).toBeInTheDocument();
  });
  it('withholds unsupported predictions and never manufactures execution evidence',()=>{
    const r=modelFixture();r.alternative.model_trace!.prediction_executed=false;r.alternative.model_trace!.support_reasons=['unsupported_regime'];r.alternative.model_scores={Budget_Overrun:null};
    expect(decode(r)).toBe(r);render(<ModelEvidence data={r}/>);
    expect(screen.getByText(/Prediction withheld/)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('unsupported_regime');
    r.alternative.model_scores={Budget_Overrun:{uncalibrated_score:.5,class:1}};
    expect(()=>decode(r)).toThrow('Withheld model');
  });
  it('rejects claimed native execution with missing scores or invalid input features',()=>{
    const r=modelFixture();r.alternative.model_scores={Budget_Overrun:null};expect(()=>decode(r)).toThrow('Missing native model score');
    const invalid=modelFixture();invalid.alternative.model_trace!.input_features={bad:NaN};expect(()=>decode(invalid)).toThrow('Invalid model features');
  });
  it('renders real API-shaped results and labels research mode',async()=>{
    render(<App/>);expect(await screen.findByText('Estimated event cost')).toBeInTheDocument();
    expect(screen.queryByText(/Research prototype — not confirmed vendor quotations/)).not.toBeInTheDocument();
    expect(screen.getByText('PlanoVision',{exact:true})).toBeInTheDocument();
    expect(screen.getByText('Spatial-Financial Intelligence and Budget Optimization',{exact:true})).toBeInTheDocument();
    expect(screen.queryByText('EventLedger')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Venue width')).toHaveValue(20);
    expect(screen.queryByLabelText(/Stage width/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:/Model evidence/}));
    expect(screen.getAllByText('Unavailable for this configuration')).toHaveLength(2);
  });
  it('recalculates What-If inputs without changing the baseline',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    fireEvent.change(screen.getByLabelText('Requested new value'),{target:{value:'160'}});
    await waitFor(()=>{
      const call=vi.mocked(fetch).mock.calls.at(-1)!;
      const body=JSON.parse(call[1]!.body as string);
      expect(body.baseline.guests).toBe(150);expect(body.alternative.guests).toBe(160);
    });
  });
  it('blocks invalid input but retains the labelled previous calculation',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.change(screen.getByLabelText('Guest count'),{target:{value:'0'}});
    expect(await screen.findByRole('alert')).toHaveTextContent('Guest count');
    expect(screen.getByText('Estimated event cost')).toBeInTheDocument();
    expect(screen.getByText('Changes pending — previous calculated result retained')).toBeInTheDocument();
  });
  it('renders spatial failures without fabricated metrics',async()=>{
    const r=fixture();r.alternative={...r.alternative,status:'blocked',plan:null,blockers:['spatially_infeasible']};r.delta=null;
    vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>r} as Response);
    render(<App/>);fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));expect(await screen.findByRole('alert')).toHaveTextContent('venue is too small');
    expect(screen.queryByText('Estimated event cost')).not.toBeInTheDocument();
  });
  it('renders budget warnings',async()=>{
    const r=fixture();r.baseline.plan!.budget_feasible=false;
    vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>r} as Response);
    render(<App/>);expect(await screen.findByText('Expense budget exceeded')).toBeInTheDocument();
  });
  it('shows the size-extrapolation warning beside calculated results',async()=>{
    const r=fixture();r.baseline.plan!.warnings.push('Extended-scope calculation only: hypothetical extrapolation, not market calibration.');
    vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>r} as Response);
    render(<App/>);expect(await screen.findByText('Extended-size research estimate — not validated market pricing.')).toBeInTheDocument();
    expect(screen.getByText('Estimated event cost')).toBeInTheDocument();
  });
  it('rejects missing/null financial results',async()=>{
    const r=fixture();r.alternative.plan=null;
    vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>r} as Response);
    render(<App/>);expect(await screen.findByRole('alert')).toHaveTextContent('Missing or invalid financial results');
  });
  it('reports unavailable backend without mock fallback',async()=>{
    vi.mocked(fetch).mockRejectedValue(new Error('Backend unavailable'));
    render(<App/>);expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable');
  });
  it('validates monetary values and response identity',()=>{
    expect(validateInputs({...defaults,guests:10,target_budget_lkr:100000})).toBeNull();
    expect(validateInputs({...defaults,guests:1000,target_budget_lkr:100000})).toBeNull();
    expect(validateInputs({...defaults,guests:5001})).toMatch(/1 to 5000/);
    expect(validateInputs({...defaults,retained_receipts_lkr:0})).toMatch(/positive/);
    expect(()=>decode({...fixture(),mode:'production'})).toThrow();
  });
  it('uses focused planner, change and report views and preserves inputs',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    expect(screen.queryByText('What does the change cost?')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Guest count'),{target:{value:'160'}});
    await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    expect(screen.queryByText(/Published reference anchors \+ explicit synthetic assumptions/)).not.toBeInTheDocument();
    expect(screen.getByText('What does the change cost?')).toBeInTheDocument();
    expect(screen.queryByText('Where the budget goes')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Guest count')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Requested new value')).toHaveValue(150);
    fireEvent.click(screen.getByRole('link',{name:/Reports & explainability/}));
    expect(screen.queryByText(/Research prototype — not confirmed vendor quotations/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Guest count')).not.toBeInTheDocument();
    expect(screen.queryByText('What does the change cost?')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:/Financial planner/}));
    expect(screen.getByLabelText('Guest count')).toHaveValue(160);
  });
  it('generates an explainable report on the dedicated report page',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:/Reports & explainability/}));
    expect(screen.queryByLabelText('Generated report')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Generate explainable report'}));
    expect(screen.getByLabelText('Generated report')).toHaveTextContent('TEST ONLY');
    expect(screen.getByRole('button',{name:'Download explainable report'})).toBeInTheDocument();
  });
  it('offers seven distinct pages and keeps calendar, storage, forecasts and model evidence off the planner',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    const nav=screen.getByRole('navigation',{name:'Workspace pages'});
    expect(nav.querySelectorAll('a')).toHaveLength(7);
    expect(screen.queryByLabelText('Venue / team calendar')).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Save main plan in this browser'})).not.toBeInTheDocument();
    expect(screen.queryByText('Model Evidence Lab')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'Booking calendar'}));
    expect(screen.getByLabelText('Venue / team calendar')).toBeInTheDocument();
    expect(screen.queryByLabelText('Guest count')).not.toBeInTheDocument();
    expect(screen.queryByText('Estimated event cost')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'Saved events'}));
    expect(screen.getByRole('button',{name:'Save main plan in this browser'})).toBeInTheDocument();
    expect(screen.queryByLabelText('Venue / team calendar')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'Price outlook'}));
    expect(screen.getByText('Future ingredient-price estimate')).toBeInTheDocument();
    expect(screen.getByText('Historical price forecasts')).toBeInTheDocument();
    expect(screen.queryByText('Health indicator & recommendations')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'Model evidence'}));
    expect(screen.getByText('Model Evidence Lab')).toBeInTheDocument();
    expect(screen.queryByText('Future ingredient-price estimate')).not.toBeInTheDocument();
    expect(screen.queryByText('Generate your decision report')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'Reports & explainability'}));
    expect(screen.getAllByText('Health indicator & recommendations')).toHaveLength(1);
    expect(screen.queryByText('Model Evidence Lab')).not.toBeInTheDocument();
    expect(screen.queryByText('Risk signals, with context')).not.toBeInTheDocument();
  });
  it('restores deep links and handles browser-history changes without resetting event inputs',async()=>{
    history.replaceState(null,'','/#/calendar');render(<App/>);
    expect(screen.getByRole('link',{name:'Booking calendar'})).toHaveAttribute('aria-current','page');
    expect(screen.getByLabelText('Venue / team calendar')).toHaveValue('');
    fireEvent.click(screen.getByRole('link',{name:'Financial planner'}));
    fireEvent.change(screen.getByLabelText('Guest count'),{target:{value:'175'}});
    history.replaceState(null,'','/#/forecast');fireEvent(window,new PopStateEvent('popstate'));
    expect(screen.getByText('Future ingredient-price estimate')).toBeInTheDocument();
    history.replaceState(null,'','/#/planner');fireEvent(window,new PopStateEvent('popstate'));
    expect(screen.getByLabelText('Guest count')).toHaveValue(175);
    history.replaceState(null,'','/#/unknown');fireEvent(window,new HashChangeEvent('hashchange'));
    expect(screen.getByRole('link',{name:'Financial planner'})).toHaveAttribute('aria-current','page');
  });
  it('keeps a draft expense across the new pages without adding it to the accepted plan',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:'What-If comparison'}));
    fireEvent.change(screen.getByLabelText('Expense name'),{target:{value:'Lighting extras'}});
    fireEvent.change(screen.getByLabelText('Estimated total amount (LKR)'),{target:{value:'25000'}});
    fireEvent.click(screen.getByRole('button',{name:'Preview addition'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm changes to main plan'})).toBeEnabled());
    for(const name of ['Saved events','Booking calendar','Price outlook','Model evidence','Reports & explainability'])fireEvent.click(screen.getByRole('link',{name}));
    expect(screen.getByText(/Report scope: unconfirmed expense preview/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'What-If comparison'}));
    expect(screen.getByRole('button',{name:'Preview removal Lighting extras'})).toBeInTheDocument();
    const call=vi.mocked(fetch).mock.calls.filter(([url])=>String(url)==='/api/planner/compare').at(-1)!;
    const body=JSON.parse(call[1]!.body as string);
    expect(body.baseline.quotes).toHaveLength(0);expect(body.alternative.quotes).toHaveLength(1);
    expect(parsePlan(localStorage.getItem(PLAN_KEY)!).quotes).toHaveLength(0);
  });
  it('renders score decomposition and grounded recommendations',async()=>{
    const r=fixture();r.insights={status:'calculated',score:{name:'Experimental financial planning coverage',value:70,status:'action_required',formula:'100 × min(budget_coverage, margin_coverage)',budget_coverage:.7,margin_coverage:1,budget_formula:'budget / cost with reserve',margin_formula:'margin / target',limitation:'Not a validated financial health score'},recommendations:[{id:'cost',title:'Seek documented cost reductions',amount_lkr:100000,rationale:'TEST ONLY: quoted savings must be confirmed'}],explainability:{method:'ledger_delta_only',drivers:[{line_item:'catering',change_lkr:50000}]}};
    vi.mocked(fetch).mockResolvedValue({ok:true,json:async()=>r} as Response);
    render(<App/>);fireEvent.click(screen.getByRole('link',{name:/Reports & explainability/}));expect(await screen.findByText('Health indicator & recommendations')).toBeInTheDocument();
    expect(screen.getByText('70.0')).toBeInTheDocument();
    expect(screen.getByText('Seek documented cost reductions')).toBeInTheDocument();
    fireEvent.click(screen.getByText('How this score is calculated'));
    expect(screen.getByText(/100 × min/)).toBeInTheDocument();
  });
  it('does not blank the result during a slow recalculation',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    let finish!:(value:Response)=>void;
    vi.mocked(fetch).mockImplementation(()=>new Promise<Response>(resolve=>{finish=resolve;}));
    fireEvent.change(screen.getByLabelText('Guest count'),{target:{value:'160'}});
    expect(screen.getByText('Estimated event cost')).toBeInTheDocument();
    await waitFor(()=>expect(finish).toBeTypeOf('function'));
    expect(screen.getByText('Changes pending — previous calculated result retained')).toBeInTheDocument();
    finish({ok:true,json:async()=>fixture()} as Response);
    await screen.findByText('Calculated result: original event');
  });
  it('retains previous result but disables exports after invalid editing',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.change(screen.getByLabelText('Maximum allowed spending'),{target:{value:''}});
    expect(screen.getByText('Estimated event cost')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:/Reports & explainability/}));
    expect(screen.getByRole('button',{name:'Generate explainable report'})).toBeDisabled();
    expect(screen.getByRole('button',{name:'Download JSON evidence'})).toBeDisabled();
  });
  it('copies the edited original plan only on explicit action',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.change(screen.getByLabelText('Guest count'),{target:{value:'50'}});
    fireEvent.click(screen.getByRole('button',{name:'Use original plan for client changes'}));
    await waitFor(()=>{
      const body=JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string);
      expect(body.baseline.guests).toBe(50);expect(body.alternative.guests).toBe(50);
    });
    expect(screen.getByLabelText('Requested new value')).toHaveValue(50);
  });
  it('uses red, yellow and green score bars without green financial breaches',()=>{
    expect(scoreBand(100,false,500000)).toBe('green');
    expect(scoreBand(90,true,10000)).toBe('yellow');
    expect(scoreBand(60,true,10000)).toBe('yellow');
    expect(scoreBand(30,true,10000)).toBe('red');
    expect(scoreBand(100,false,-1)).toBe('red');
    render(<ScoreBar value={0} actionRequired profit={-100}/>);
    const meter=screen.getByRole('progressbar',{name:'Experimental financial planning score'});
    expect(meter).toHaveAttribute('aria-valuenow','0');expect(meter).toHaveClass('band-red');
  });
  it('keeps calculator, KPI cards, score and reports on their owning pages only',async()=>{
    render(<App/>);await screen.findByText('Estimated event cost');
    expect(screen.getByText('Original event setup')).toBeInTheDocument();
    expect(screen.queryByText('Health indicator & recommendations')).not.toBeInTheDocument();
    expect(screen.queryByText('Try an expense change')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    expect(screen.getByText('Try an expense change')).toBeInTheDocument();
    expect(screen.getByText('What does the change cost?')).toBeInTheDocument();
    expect(screen.queryByText('Original event setup')).not.toBeInTheDocument();
    expect(screen.queryByText('Estimated event cost')).not.toBeInTheDocument();
    expect(screen.queryByText('Health indicator & recommendations')).not.toBeInTheDocument();
    expect(screen.queryByText('Risk signals, with context')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:/Reports & explainability/}));
    expect(screen.getByText('Health indicator & recommendations')).toBeInTheDocument();
    expect(screen.getByText('Generate your decision report')).toBeInTheDocument();
    expect(screen.queryByText('Original event setup')).not.toBeInTheDocument();
    expect(screen.queryByText('Estimated event cost')).not.toBeInTheDocument();
    expect(screen.queryByText('Try an expense change')).not.toBeInTheDocument();
    expect(screen.queryByText('What does the change cost?')).not.toBeInTheDocument();
  });
  it('previews expenses without committing, then confirms or discards explicitly',async()=>{
    vi.mocked(fetch).mockImplementation(async(_url,options)=>{
      const body=JSON.parse(options!.body as string);const r=fixture();
      for(const key of ['baseline','alternative'] as const){
        const state=body[key];const extra=state.quotes.filter((q:any)=>!state.removed_quote_ids.includes(q.id)).reduce((sum:number,q:any)=>sum+q.unit_rate_lkr,0);
        r[key].plan!.total_cost_lkr+=extra;r[key].plan!.expected_profit_lkr-=extra;
      }
      r.delta!.cost_lkr=r.alternative.plan!.total_cost_lkr-r.baseline.plan!.total_cost_lkr;r.delta!.profit_lkr=-r.delta!.cost_lkr;
      return {ok:true,json:async()=>r} as Response;
    });
    render(<App/>);await screen.findByText('Estimated event cost');
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    expect(screen.queryByLabelText('Service identifier')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Expense name'),{target:{value:'Fireworks'}});
    fireEvent.change(screen.getByLabelText('Estimated total amount (LKR)'),{target:{value:'50000'}});
    fireEvent.click(screen.getByRole('button',{name:'Preview addition'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm changes to main plan'})).toBeEnabled());
    let request=JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string);
    expect(request.baseline.quotes).toHaveLength(0);expect(request.alternative.quotes).toHaveLength(1);
    expect(request.alternative.quotes[0].source_kind).toBe('planner_entered_assumption');
    fireEvent.click(screen.getByRole('link',{name:/Financial planner/}));
    expect(screen.getByText('Estimated event cost').parentElement).toHaveTextContent('1,570,450.20');
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    fireEvent.click(screen.getByRole('button',{name:'Confirm changes to main plan'}));
    await waitFor(()=>{request=JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string);expect(request.baseline.quotes).toHaveLength(1);});
    expect(parsePlan(localStorage.getItem(PLAN_KEY)!).quotes).toHaveLength(1);
    fireEvent.click(screen.getByRole('link',{name:/Financial planner/}));
    await waitFor(()=>expect(screen.getByText('Estimated event cost').parentElement).toHaveTextContent('1,620,450.20'));
    fireEvent.click(screen.getByRole('link',{name:/What-If comparison/}));
    fireEvent.click(screen.getByRole('button',{name:'Preview removal Fireworks'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm changes to main plan'})).toBeEnabled());
    request=JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string);
    expect(request.baseline.removed_quote_ids).toHaveLength(0);expect(request.alternative.removed_quote_ids).toHaveLength(1);
    fireEvent.click(screen.getByRole('button',{name:'Discard preview'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Confirm changes to main plan'})).toBeDisabled());
    await waitFor(()=>{
      request=JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string);
      expect(request.baseline.removed_quote_ids).toHaveLength(0);expect(request.alternative.removed_quote_ids).toHaveLength(0);
    });
  });
});
