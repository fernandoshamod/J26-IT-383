import {validateInputs,type Inputs} from './api';

// Blank editor state is never serialized or sent to the calculation API.
export function blankEvent():Inputs {
  return {event_type:'',event_date:'',guests:NaN,event_hours:NaN,
    venue_width_m:NaN,venue_length_m:NaN,target_budget_lkr:NaN,
    retained_receipts_lkr:NaN,min_profit_margin_pct:NaN,quotes:[],removed_quote_ids:[]};
}
export function tomorrowLocal(now=new Date()):string {
  const date=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1);
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
}
export function validateEventSetup(value:Inputs,now=new Date()):string|null {
  if(value.event_date && value.event_date<tomorrowLocal(now))return 'Choose a future event date (tomorrow or later).';
  return validateInputs(value);
}
