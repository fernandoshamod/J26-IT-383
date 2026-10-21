import {decodeGraphRisk,type GraphRisk} from './GraphRiskPanel';
export type Quote = {id:string;label:string;mode:'add'|'replace';service:string;quantity_basis:string;unit_rate_lkr:number|null;tax_scope:string;service_pct:number|null;tax_pct:number|null;pricing_policy:string;increase_pct:number|null;source_kind:string;evidence_ref:string;valid_from:string;valid_until:string;covers:string[];committed:boolean;cancellation_fee_lkr:number|null};
export type Inputs={event_type:''|'Wedding'|'Corporate';event_date:string;guests:number;event_hours:number;venue_width_m:number;venue_length_m:number;target_budget_lkr:number;retained_receipts_lkr:number;min_profit_margin_pct:number;quotes:Quote[];removed_quote_ids:string[]};
export type Plan={total_cost_lkr:number;expected_profit_lkr:number;expected_margin_pct:number;reserve_lkr:number;budget_headroom_lkr:number;retained_receipts_lkr:number;recommended_client_price_excluding_output_tax_lkr:number;budget_feasible:boolean;affordable_after_reserve:boolean;margin_feasible:boolean;space_utilization:number;used_area_m2:number;seats:number;tables:number;staff:number;line_items_lkr:Record<string,number>;warnings:string[]};
export type Result={status:string;plan:Plan|null;blockers:string[];model_scores:Record<string,{uncalibrated_score:number;class:number}|null>|null;model_support?:unknown;geometry?:{venue_area_m2:number;area_rule_capacity:number;guests_per_m2:number};monte_carlo:{overrun_frequency:number;margin_risk_frequency:number;cost_lkr:{p05:number;p95:number;mean:number}}|null;draft_planning_health:{score_points:number}|null;shap_drivers?:Record<string,{feature:string;contribution_log_odds:number}[]|null>|null;graph_risk?:GraphRisk};
export type Insights={status:string;reason?:string;score:{name:string;value:number;status:string;formula:string;budget_coverage:number;margin_coverage:number;budget_formula:string;margin_formula:string;limitation:string}|null;recommendations:{id:string;title:string;amount_lkr:number|null;rationale:string}[];explainability:{method:string;drivers:{line_item:string;change_lkr:number}[];model_explanation_available?:boolean;model_explanation_note?:string}};
export type ModelMetrics={accuracy:number;balanced_accuracy:number;precision:number;recall:number;f1:number;roc_auc:number;log_loss:number;brier_score:number;tn:number;fp:number;fn:number;tp:number};
export type TrainingEvaluation={selection:string;test_scope:string;previously_inspected_test:boolean;threshold:number;test_used_for_selection:boolean;data_or_labels_or_splits_changed:boolean;protocol_sha256:string;source_run:string;split_roots:Record<string,number>;split_rows:Record<string,number>;targets:Record<string,{nested_cv:{oof_metrics:ModelMetrics;original_oof_metrics:ModelMetrics;accuracy_fold_sd:number};folds:{fold:number;accuracy:number;chosen_candidate:string}[];features:string[];training_search:{candidate:string;mean_log_loss:number}[];deployment:{training_cv_winner:string;validation_gate_pass:boolean;deployed:string};test:{xgboost:ModelMetrics;original_v3:ModelMetrics;prior:ModelMetrics;planning_rule_class_accuracy:number;family_bootstrap:{accuracy_95_interval:number[];accuracy_difference_vs_v3_95_interval:number[];families:number};by_event_type:Record<string,ModelMetrics>}}>};
export type ModelTrace={run_id:string;method:string;prediction_executed:boolean;training_rows:number;test_rows:number;independent_root_families:number;feature_count:number;input_features:Record<string,number>|null;model_sha256:Record<string,string>;design_sha256:string;support_reasons:string[];test_metrics:Record<string,{xgboost:{accuracy:number;roc_auc:number};planning_rule_class_accuracy:number}>;limitations:string[];shap_additivity_verified?:boolean;model_features?:Record<string,string[]>;evaluation?:TrainingEvaluation};
export type PricingScope={event_date:string;calibrated_future_forecast_applied:false;entire_event_supplier_verified:false;statement:string;lines:{line_key:string;amount_lkr:number;basis:string;tax_scope:string;price_terms:string;documented_increase_pct:number|null;evidence_ref:string;independently_verified:false}[]};
export type Comparison={api_version:string;mode:string;baseline:Result & {model_trace?:ModelTrace};alternative:Result & {model_trace?:ModelTrace};delta:{cost_lkr:number;profit_lkr:number;margin_pct_points:number;line_changes_lkr:Record<string,number>}|null;report_text:string;insights?:Insights;pricing_scope?:{baseline:PricingScope;alternative:PricingScope};provenance:{configuration_sha256:string;model_run:string;live_vendor_fetch:boolean}};
export const defaults:Inputs={event_type:'Wedding',event_date:'2026-10-22',guests:150,event_hours:5,venue_width_m:20,venue_length_m:25,target_budget_lkr:2000000,retained_receipts_lkr:2500000,min_profit_margin_pct:15,quotes:[],removed_quote_ids:[]};
const finite=(x:unknown):x is number=>typeof x==='number'&&Number.isFinite(x);
export function validateInputs(x:Inputs):string|null {
  if(!['Wedding','Corporate'].includes(x.event_type))return 'Choose an event type.';
  for(const [key,value] of Object.entries(x))if(typeof value==='number'&&!finite(value))return 'Please enter valid numbers.';
  if(!Number.isInteger(x.guests)||x.guests<1||x.guests>5000)return 'Guest count must be an integer from 1 to 5000. Extended-size estimates are experimental; model support is checked separately.';
  if(x.event_hours<2||x.event_hours>12)return 'Event duration must be 2–12 hours.';
  if(x.venue_width_m<=0||x.venue_length_m<=0)return 'Venue dimensions must be positive.';
  if(x.target_budget_lkr<=0||x.retained_receipts_lkr<=0)return 'Budget and expected client payment must be positive.';
  if(x.min_profit_margin_pct<0||x.min_profit_margin_pct>40)return 'Minimum margin must be 0–40%.';
  if(!/^\d{4}-\d{2}-\d{2}$/.test(x.event_date))return 'Choose an event date.';
  return null;
}
export function decode(data:any):Comparison {
  for(const key of ['baseline','alternative'])if(data?.[key]?.graph_risk)decodeGraphRisk(data[key].graph_risk);
  if(data?.pricing_scope)for(const key of ['baseline','alternative']){
    const s=data.pricing_scope[key];
    if(!s||typeof s.statement!=='string'||typeof s.event_date!=='string'||s.calibrated_future_forecast_applied!==false||s.entire_event_supplier_verified!==false||!Array.isArray(s.lines)||s.lines.some((v:any)=>!v||!finite(v.amount_lkr)||v.independently_verified!==false||!['line_key','basis','tax_scope','price_terms','evidence_ref'].every(k=>typeof v[k]==='string')||v.documented_increase_pct!==null&&!finite(v.documented_increase_pct)))throw Error('Invalid price-scope evidence.');
  }
  if(data?.api_version!=='lkr-dashboard.0.1'||data.mode!=='research_only'||typeof data.report_text!=='string'||typeof data.provenance?.configuration_sha256!=='string')throw new Error('Invalid API response; no results displayed.');
  for(const key of ['baseline','alternative']){
    const r=data[key];
    if(!r||!Array.isArray(r.blockers)||!['calculated','blocked','quotation_required'].includes(r.status))throw new Error('Invalid calculation response.');
    if(r.status==='calculated'){
      const p=r.plan;
      if(!p||!['total_cost_lkr','expected_profit_lkr','expected_margin_pct','reserve_lkr','budget_headroom_lkr','retained_receipts_lkr','recommended_client_price_excluding_output_tax_lkr','space_utilization','used_area_m2','seats','tables','staff'].every(k=>finite(p[k]))||!Array.isArray(p.warnings)||!p.line_items_lkr||!Object.values(p.line_items_lkr).every(finite))throw new Error('Missing or invalid financial results.');
      if(!['budget_feasible','affordable_after_reserve','margin_feasible'].every(k=>typeof p[k]==='boolean'))throw new Error('Missing constraint results.');
      if(!r.monte_carlo||!finite(r.monte_carlo.overrun_frequency)||!finite(r.monte_carlo.margin_risk_frequency)||!['p05','p95','mean'].every(k=>finite(r.monte_carlo.cost_lkr?.[k])))throw new Error('Invalid simulation results.');
    }else if(r.plan!==null)throw new Error('Blocked results must not contain a financial plan.');
  }
  if(data.delta!==null&&!['cost_lkr','profit_lkr','margin_pct_points'].every(k=>finite(data.delta?.[k])))throw new Error('Invalid What-If results.');
  if(data.insights){
    const v=data.insights;
    if(!Array.isArray(v.recommendations)||!Array.isArray(v.explainability?.drivers))throw new Error('Invalid planning insights.');
    if(v.score&&(!finite(v.score.value)||v.score.value<0||v.score.value>100||!finite(v.score.budget_coverage)||!finite(v.score.margin_coverage)))throw new Error('Invalid planning score.');
    if(v.recommendations.some((x:any)=>typeof x.title!=='string'||typeof x.rationale!=='string'||x.amount_lkr!==null&&!finite(x.amount_lkr)))throw new Error('Invalid recommendation.');
  }
  for(const key of ['baseline','alternative']){
    const r=data[key],t=r.model_trace;
    if(t){
      if(typeof t.run_id!=='string'||typeof t.method!=='string'||typeof t.prediction_executed!=='boolean'||!Array.isArray(t.support_reasons)||!Array.isArray(t.limitations)||!t.model_sha256||!t.test_metrics||typeof t.design_sha256!=='string'||!['training_rows','test_rows','feature_count','independent_root_families'].every(k=>finite(t[k])))throw new Error('Invalid trained-model execution evidence.');
      if(t.input_features!==null&&(!t.input_features||!Object.values(t.input_features).every(finite)||Object.keys(t.input_features).length!==t.feature_count))throw new Error('Invalid model features.');
      for(const [target,m] of Object.entries(t.test_metrics) as [string,any][]){
        const score=r.model_scores?.[target];
        if(!finite(m?.xgboost?.accuracy)||!finite(m?.planning_rule_class_accuracy))throw new Error('Invalid model evaluation evidence.');
        if(t.prediction_executed&&(!score||!finite(score.uncalibrated_score)||score.uncalibrated_score<0||score.uncalibrated_score>1||![0,1].includes(score.class)))throw new Error('Missing native model score.');
        if(!t.prediction_executed&&score!==null)throw new Error('Withheld model must not report a score.');
      }
      if(t.evaluation){
        const e=t.evaluation;
        if(e.test_used_for_selection!==false||typeof e.previously_inspected_test!=='boolean'||typeof e.test_scope!=='string'||typeof e.selection!=='string'||!e.targets)throw new Error('Invalid training evaluation protocol.');
        for(const v of Object.values(e.targets) as any[]){
          const all=[v.test?.xgboost,v.test?.original_v3,v.test?.prior,v.nested_cv?.oof_metrics,v.nested_cv?.original_oof_metrics,...Object.values(v.test?.by_event_type||{})];
          if(all.some(m=>!m||!['accuracy','balanced_accuracy','precision','recall','f1','roc_auc','log_loss','brier_score','tn','fp','fn','tp'].every(k=>finite(m[k]))))throw new Error('Invalid training evaluation metrics.');
          if(!Array.isArray(v.features)||!Array.isArray(v.folds)||!Array.isArray(v.training_search)||!Array.isArray(v.test?.family_bootstrap?.accuracy_95_interval)||v.test.family_bootstrap.accuracy_95_interval.length!==2||!v.test.family_bootstrap.accuracy_95_interval.every(finite))throw new Error('Missing grouped evaluation details.');
        }
      }
    }
  }
  return data;
}
export async function compare(baseline:Inputs,alternative:Inputs,signal?:AbortSignal):Promise<Comparison>{
  const response=await fetch('/api/planner/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({baseline,alternative}),signal});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'Calculation failed.');
  return decode(data);
}
