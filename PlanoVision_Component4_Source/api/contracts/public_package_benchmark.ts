// Separate from FinancialResponse: partial package costs cannot become full budgets.
export interface PackageBenchmark {
  api_version: 'benchmark.0.1';
  result_kind: 'public_advertised_package_benchmark';
  is_trained_model_prediction: false;
  is_observed_event_outcome: false;
  eligible_as_financial_risk_training_record: false;
  currency: 'LKR'; evidence_id: string; provider: string; package: string;
  event_type: 'Wedding' | 'Corporate'; planned_guests: number; event_date: string | null;
  published_rate_lkr_per_person: number; published_price_kind: string;
  advertised_package_amount_lkr: number; published_charge_amount_lkr: number | null;
  published_charge_kind: 'service_charge' | 'unspecified_surcharge' | 'unresolved';
  known_components_subtotal_lkr: number; charge_calculation_assumption: string | null;
  confirmed_all_in_package_total_lkr: null; complete_event_total_lkr: null;
  actual_cost_lkr: null; profit_lkr: null; risk_labels: null;
  source_url: string; source_access_date: string; warnings: string[];
}
export interface PackageComparison {
  api_version: 'benchmark.0.1';
  comparison_kind: 'advertised_package_component_what_if';
  is_trained_model_prediction: false;
  baseline: PackageBenchmark; alternative: PackageBenchmark;
  delta: {planned_guests: number; known_components_subtotal_lkr: number;
    full_event_cost_lkr: null; profit_lkr: null; space_utilization: null; risk_probability: null};
  full_budget_feasibility: 'unavailable_incomplete_event_costs'; explanation: string;
}
