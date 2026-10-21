// Research-only, separate from LKR live/dashboard response contracts.
export interface UnitlessInputs {
  guests: number; event_hours: number; stage_width_m: number; stage_length_m: number;
  budget_score: number; retained_receipts_score: number;
}
export interface SimulationSummary { mean: number; p05: number; p50: number; p95: number }
export interface UnitlessResult {
  status: 'calculated' | 'blocked'; event_type: 'Wedding' | 'Corporate'; inputs: UnitlessInputs;
  planned: {
    line_items_score: Record<string, number>; total_cost_score: number; expected_revenue_score: number;
    expected_profit_score: number; expected_margin_points: number | null; reserve_score: number;
    required_min_margin_points: number; planned_margin_feasible: boolean | null;
    operating_allowance_score: number; budget_feasible: boolean; operating_allowance_feasible: boolean;
    budget_utilization: number; used_area_m2: number; usable_area_m2: number; space_utilization: number;
    capacity_persons: number; seats: number; staff: number; tables: number; paid_hours_per_staff: number;
    quantities: Record<string, number>; estimate_kind: 'deterministic_rule_based_not_ML_cost_forecast';
  } | null;
  model_risk_scores: {
    origin: 'saved_XGBoost_uncalibrated_classifier_scores'; calibrated: false;
    Budget_Overrun: number | null; Profit_Margin_Risk: number | null; Vendor_Cost_Anomaly: null;
    model_support_status: string; out_of_support_features: string[];
  } | null;
  monte_carlo: {
    origin: 'hypothetical_simulated_outcomes_not_observed'; cost_score: SimulationSummary | null;
    revenue_score: SimulationSummary | null; profit_score: SimulationSummary | null;
    margin_points: SimulationSummary | null; budget_overrun_frequency: number;
    profit_margin_risk_frequency: number; planned_operating_allowance_exceeded_frequency: number;
    quantile_interpretation: 'simulation_distribution_not_calibrated_prediction_interval';
  } | null;
  financial_health_score: null; warnings: string[]; blockers: string[];
}
export interface UnitlessProvenance {
  warning: string; cost_unit: 'dimensionless_score'; currency: null; configuration_sha256: string;
  release_sha256: string; model_run: string; model_sha256: Record<string,string>; numpy_version: string;
  simulation_method: string; draws: number; seed: number; observed_event_outcomes: false;
  scientific_limitations: string[];
}
export type UnitlessResponse = {
  api_version: 'unitless-decision.0.1'; provenance: UnitlessProvenance;
} & ({operation:'calculate';result:UnitlessResult} | {
  operation:'what-if';baseline:UnitlessResult;alternative:UnitlessResult;
  comparison_status:'comparable'|'blocked';delta: {
    planned_cost_score:number;expected_profit_score:number;space_utilization:number;seats:number;staff:number;
    budget_overrun_frequency:number;paired_simulated_cost_difference_score:SimulationSummary|null;
    paired_simulated_profit_difference_score:SimulationSummary|null;
  } | null;
});
