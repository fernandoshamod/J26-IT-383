import type { UnitlessResponse } from './unitless_decision';
export interface DraftPlanningHealth {
  api_version: 'experimental-indicators.0.1'; operation: 'planning-health'; decision: UnitlessResponse;
  indicator: {
    status:'experimental'|'unavailable'; score:number|null; reason:string|null;
    real_world_financial_health_score:null;
    components:{budget_and_earmarked_reserve_coverage:number;minimum_margin_coverage:number}|null;
    policy:{version:string;approval_status:'proposed_not_formally_approved';empirically_validated:false;
      origin:string;formula:string;interpretation:string;unit:string};
  };
}
export interface ComparisonLine {
  line_id:string;service:string;unit:string;currency:string;quantity:number;unit_rate:number;date:string;
  tax_scope:string;included_services:string[];bundle_id:string|null;evidence_reference:string;
}
export interface QuoteInvoiceRequest {
  quote:ComparisonLine[];invoice:ComparisonLine[];relative_rate_tolerance:number;
  evidence_kind:'mock_test_only'|'user_supplied_unverified';
}
export interface QuoteInvoiceResponse {
  api_version:'experimental-indicators.0.1';operation:'quote-invoice-comparison';origin:string;
  evidence_kind:QuoteInvoiceRequest['evidence_kind'];source_verified:false;
  policy:{relative_rate_tolerance:number;origin:string};Vendor_Cost_Anomaly_prediction:null;warnings:string[];
  line_comparisons:{line_id:string;status:'comparable'|'manual_review';rate_increase_flag:boolean|null;
    relative_rate_change:number|null;rate_effect_amount:number|null;quantity_effect_amount:number|null;
    total_difference_amount:number|null;currency:string|null;reasons:string[]}[];
}
