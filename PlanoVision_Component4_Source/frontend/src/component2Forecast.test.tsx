import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import Component2Import from './Component2Import';
import {ForecastForm,decodeReplay} from './HistoricalForecastPanel';
import {defaults} from './api';
const series={series_id:'S003:Anamalu:1 Kg.',unit:'LKR/1 Kg.',selected_model:'prophet',forecast_origin:'2025-07-01',first_replay_month:'2025-08-01',last_replay_month:'2026-09-01',source_id:'S003',scope:'ingredient_component',validation_mae_in_series_unit:8.861403715399783};
const catalog={version:'historical-forecast-bridge.v1',mode:'archived_retrospective_replay_only',series:[series],limitations:['TEST: archived context only; never a whole event budget']};
const replay={status:'available_historical_replay',mode:'archived_retrospective_replay_only',series_id:series.series_id,unit:series.unit,model:'prophet',forecast_origin:'2025-07-01',last_supported_month:'2026-09-01',target_month:'2025-08-01',forecast_yhat:320.6111238665773,ingredient_subtotal_lkr:3206.11,applied_to_event_budget:false,calibrated_current_event_forecast:false,reason:'not_a_current_event_forecast'};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('Component 2 adapter UI',()=>{
  it('imports proposed inputs only, without confirming or inventing verification',async()=>{
    const onImport=vi.fn();vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({contract_version:'component2.quotation_bundle.v1',status:'proposed_inputs_only',independently_verified:false,transport_authenticated:false,bundle_id:'TEST-BUNDLE',proposed_state:defaults})})));
    render(<Component2Import state={defaults} onImport={onImport}/>);
    fireEvent.change(screen.getByLabelText('Component 2 quotation JSON'),{target:{files:[{size:10,text:async()=>'TEST raw JSON passed unchanged'}]}});
    await waitFor(()=>expect(onImport).toHaveBeenCalledWith(defaults));
    const payload=JSON.parse(vi.mocked(fetch).mock.calls[0][1]!.body as string);expect(payload.bundle_json).toBe('TEST raw JSON passed unchanged');
    expect(screen.getByRole('status')).toHaveTextContent('preview only');
  });
  it('rejects server errors and unsupported verification claims',async()=>{
    const onImport=vi.fn();vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,json:async()=>({error:'component2_currency_must_be_LKR_no_implicit_fx'})})));
    render(<Component2Import state={defaults} onImport={onImport}/>);
    fireEvent.change(screen.getByLabelText('Component 2 quotation JSON'),{target:{files:[{size:2,text:async()=>'{}'}]}});
    expect(await screen.findByText(/import rejected: component2_currency/)).toBeInTheDocument();expect(onImport).not.toHaveBeenCalled();
  });
});
describe('Historical forecast scope gates',()=>{
  it('renders a source-identified partial historical replay, not a package forecast',async()=>{
    vi.stubGlobal('fetch',vi.fn(async(url)=>({ok:true,json:async()=>String(url).endsWith('forecast-catalog')?catalog:replay})));
    render(<ForecastForm eventDate="2025-08-22"/>);await screen.findByLabelText('Forecast month');
    fireEvent.change(screen.getByLabelText('Quantity in published unit'),{target:{value:'10'}});
    fireEvent.click(screen.getByRole('button',{name:'Check historical forecast coverage'}));
    expect(await screen.findByText(/Partial ingredient illustration: LKR 3206.11/)).toBeInTheDocument();
    expect(screen.getByText('Historical replay only — not a current event forecast')).toBeInTheDocument();
    const call=vi.mocked(fetch).mock.calls.at(-1)!;expect(JSON.parse(call[1]!.body as string).expense_scope).toBe('ingredient_component');
  });
  it('shows the October coverage blocker without a substitute amount',async()=>{
    const blocked={...replay,status:'blocked',target_month:'2026-10-01',forecast_yhat:null,ingredient_subtotal_lkr:null,reason:'target_month_outside_archived_forecast_coverage'};
    vi.stubGlobal('fetch',vi.fn(async(url)=>({ok:true,json:async()=>String(url).endsWith('forecast-catalog')?catalog:blocked})));
    render(<ForecastForm eventDate="2026-10-22"/>);await screen.findByLabelText('Forecast month');
    fireEvent.click(screen.getByRole('button',{name:'Check historical forecast coverage'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('outside archived forecast coverage');
    expect(screen.queryByText(/Partial ingredient illustration/)).not.toBeInTheDocument();
  });
  it('rejects fake calibration, budget application and nonfinite forecasts',()=>{
    expect(()=>decodeReplay({...replay,calibrated_current_event_forecast:true})).toThrow();
    expect(()=>decodeReplay({...replay,applied_to_event_budget:true})).toThrow();
    expect(()=>decodeReplay({...replay,forecast_yhat:NaN})).toThrow();
  });
});
