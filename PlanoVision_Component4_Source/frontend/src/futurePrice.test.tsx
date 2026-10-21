import {afterEach,it,expect,vi} from 'vitest';
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import {FuturePriceForm,decodeFutureForecast,decodeFutureCatalog} from './FuturePricePanel';
const s={series_id:'S003:Mysore Dhall - ( Average ):1 Kg.',unit:'LKR/1 Kg.',source_id:'S003',method:'prophet',forecast_origin:'2026-09-01',first_forecast_month:'2026-10-01',last_forecast_month:'2026-12-01',training_records:45,training_quality_flag_count:0,scope:'ingredient_component'};
const catalog={version:'future-price-deployment.0.1',mode:'exploratory_full_history_deployment',series:[s],limitations:['TEST: no package conversion'],manifest_sha256:'test',new_independent_accuracy_estimate:null,applied_to_event_budget:false};
const forecast={status:'available_experimental_forecast',mode:catalog.mode,unit:s.unit,model:'prophet',target_month:'2026-10-01',forecast_origin:s.forecast_origin,last_supported_month:s.last_forecast_month,forecast_yhat:330,last_observed_y:331,ingredient_subtotal_lkr:3300,ingredient_change_from_last_observation_lkr:-10,training_quality_flag_count:0,reason:'unflagged_snapshot_not_independently_market_validated',manifest_sha256:'test',new_independent_accuracy_estimate:null,applied_to_event_budget:false,calibrated_current_event_forecast:false};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
function mock(result:any,sourceCatalog:any=catalog){vi.stubGlobal('fetch',vi.fn(async url=>({ok:true,json:async()=>String(url).endsWith('catalog')?sourceCatalog:result})));}
it('renders an October future ingredient forecast, never an applied package cost',async()=>{
  mock(forecast);render(<FuturePriceForm eventDate="2026-10-22"/>);await screen.findByLabelText('Future forecast month');
  fireEvent.change(screen.getByLabelText('Ingredient quantity in published unit'),{target:{value:'10'}});
  fireEvent.click(screen.getByRole('button',{name:'Estimate future ingredient price'}));
  expect(await screen.findByText('Ingredient-only estimate: LKR 3300.00')).toBeInTheDocument();
  expect(screen.getByText(/Not added to the event budget/)).toBeInTheDocument();
  expect(JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string).quantity).toBe(10);
});
it('does not substitute money for a source-review blocker',async()=>{
  mock({...forecast,status:'review_required',training_quality_flag_count:8,ingredient_subtotal_lkr:null,ingredient_change_from_last_observation_lkr:null,reason:'training_source_quality_review_required_no_monetary_conversion'});
  render(<FuturePriceForm eventDate="2026-10-22"/>);await screen.findByLabelText('Future forecast month');fireEvent.click(screen.getByRole('button',{name:'Estimate future ingredient price'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('source quality review');expect(screen.queryByText(/Ingredient-only estimate/)).not.toBeInTheDocument();
});
it('rejects manufactured calibration, index money, flagged conversion and nonfinite values',()=>{
  for(const x of [{...forecast,applied_to_event_budget:true},{...forecast,calibrated_current_event_forecast:true},{...forecast,unit:'index'},{...forecast,training_quality_flag_count:1},{...forecast,forecast_yhat:NaN},{...forecast,new_independent_accuracy_estimate:.99}])expect(()=>decodeFutureForecast(x)).toThrow();
  expect(()=>decodeFutureCatalog({...catalog,new_independent_accuracy_estimate:.99})).toThrow();
});
it('validates quantities before issuing forecast requests',async()=>{
  mock(forecast);render(<FuturePriceForm eventDate="2026-10-22"/>);await screen.findByLabelText('Future forecast month');
  fireEvent.change(screen.getByLabelText('Ingredient quantity in published unit'),{target:{value:''}});fireEvent.click(screen.getByRole('button',{name:'Estimate future ingredient price'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('positive quantity');expect(vi.mocked(fetch).mock.calls.length).toBe(1);
});
const review={version:'historical-source-review.0.3',manifest_sha256:'a'.repeat(64),source_snapshot_sha256:'b'.repeat(64),original_flags_preserved:true,reviewed_records:45,model_value_unresolved_count:0,publisher_period_conflict_count:1,independent_market_validation:false,review_method:'TEST ONLY retained source column match'};
it('allows reviewed model values without erasing flags and discloses publisher title conflicts',async()=>{
  const reviewed={...forecast,training_records:45,training_quality_flag_count:8,quality_review:review};
  mock(reviewed,{...catalog,series:[{...s,training_quality_flag_count:8,quality_review:review}]});
  render(<FuturePriceForm eventDate="2026-10-22"/>);await screen.findByText('Model-value source review');
  expect(screen.getByText(/Original training source flags retained: 8/)).toBeInTheDocument();
  expect(screen.getByText(/Unresolved model values: 0. Publisher period-title conflicts retained: 1/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Estimate future ingredient price'}));expect(await screen.findByText('Ingredient-only estimate: LKR 3300.00')).toBeInTheDocument();
});
it('rejects incomplete, unresolved or manufactured source-review clearances',()=>{
  const reviewed={...forecast,training_records:45,training_quality_flag_count:8,quality_review:review};
  expect(decodeFutureForecast(reviewed)).toBe(reviewed);
  for(const q of [{...review,original_flags_preserved:false},{...review,independent_market_validation:true},{...review,manifest_sha256:'z'.repeat(64)},{...review,reviewed_records:1},{...review,model_value_unresolved_count:1}])expect(()=>decodeFutureForecast({...reviewed,quality_review:q})).toThrow();
});
