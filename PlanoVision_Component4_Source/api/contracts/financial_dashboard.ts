// Transport contract 0.1.0. No trained predictions exist in this prototype.
export type EventType = 'Wedding' | 'Corporate';
export interface LineItem {
  item_id: string; category: string; quantity: number; unit: string;
  rate_lkr: number | null; net_lkr: number; tax_lkr: number; gross_lkr: number;
  included_in: string | null; evidence_ref?: string; tax_scope?: 'inclusive' | 'exclusive';
}
export interface FinancialResponse {
  api_version: '0.1.0'; status: 'blocked' | 'calculated'; event_type: EventType;
  provenance: {
    result_kind: 'deterministic_rule_estimate' | 'mock_test_fixture';
    is_trained_model_prediction: false; model_version: null;
    rules_version: string; config_version: string | null; config_sha256: string; warning: string;
  };
  costs: null | {currency: 'LKR'; estimate_lkr: number; estimate_kind: 'deterministic_rule_estimate' | 'mock_test_rule_estimate'; uncertainty_interval: null; line_items: LineItem[]};
  budget_constraints: null | {initial_budget_lkr: number; contingency_reserve_lkr: number; operating_allowance_lkr: number; headroom_lkr: number; reserve_is_expense: false};
  risk_indicators: null | {planned_budget_breach: boolean; planned_operating_allowance_breach: boolean; expected_profit_lkr: number; expected_margin_points: number | null; minimum_margin_points: number; planned_margin_shortfall: boolean | null; predicted_probabilities: null};
  spatial: null | {usable_area_m2: number; used_area_m2: number; stage_area_m2: number; space_utilization: number; planned_seats: number; capacity_persons: number; layout_origin: string; safety_certification: false};
  operations: null | {general_staff_count: number; person_hours: number; overtime_person_hours: number; furniture_tables: number; av_kits: number; lighting_kits: number};
  outcome_labels: {Budget_Overrun: 0 | 1 | null; Profit_Margin_Risk: 0 | 1 | null; Vendor_Cost_Anomaly: 0 | 1 | null; label_origin: 'unavailable' | 'mock_test_fixture'; Profit?: number | null; Profit_Margin?: number | null};
  financial_health_score: null; blockers: string[];
}
export interface WhatIfResponse {
  api_version: '0.1.0'; comparison_kind: 'paired_deterministic_what_if';
  is_trained_model_prediction: false; comparison_status: 'comparable' | 'blocked';
  changes: Record<string, number>; baseline: FinancialResponse; alternative: FinancialResponse;
  delta: null | {estimated_cost_lkr: number; expected_profit_lkr: number; used_area_m2: number};
}
