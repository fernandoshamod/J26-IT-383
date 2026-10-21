"""Strict planner-facing adapter. Financial rules/models remain frozen inputs."""
import math
from copy import deepcopy
from .lkr_research import defaults
from .planner_services import PlannerServices, report_text, iso
from .planner_insights import insights, insight_report
from .pricing_disclosure import pricing_disclosure

FIELDS={'event_type','event_date','guests','event_hours','venue_width_m','venue_length_m',
        'target_budget_lkr','retained_receipts_lkr','min_profit_margin_pct','quotes','removed_quote_ids'}


class PlannerDashboard:
    def __init__(self, *, use_expense_model=True, use_enhanced_model=True, extended_calculator_scope=False):
        self.risk=None
        if use_expense_model:
            from .expense_risk import CalculationOnlyService
            from .expense_risk_inference import ExpenseRiskInference
            if use_enhanced_model:
                from .enhanced_risk_inference import EnhancedRiskInference
                self.risk=EnhancedRiskInference()
            else:self.risk=ExpenseRiskInference()
            if extended_calculator_scope:
                from .planner_calculation_scope import PlannerCalculationService
                self.planner=PlannerServices(PlannerCalculationService())
            else:self.planner=PlannerServices(CalculationOnlyService())
        else:self.planner=PlannerServices()

    def config(self):
        inputs=defaults(self.planner.service.config)
        example={k:inputs[k] for k in FIELDS if k in inputs}
        example.update(event_date='2026-10-22',venue_width_m=20.,venue_length_m=25.,quotes=[],removed_quote_ids=[])
        return {'version':'lkr-dashboard.0.1','mode':'research_only','default_state':example,
                'app_revision':'planner-extended-scope.20261019' if hasattr(self.planner.service,'scope') else 'planner-lkr-graph-local-llm.20261018',
                'domains':self.planner.service.config['domains'],
                'stage_policy':'Fixed 4 x 6 m demo stage; no Component 1 integration',
                'live_enabled':False,'model_run':self.risk.run_id if self.risk else self.planner.service.metadata['run_id']}

    def state(self, value):
        if not isinstance(value,dict) or set(value)!=FIELDS:
            raise ValueError('exact_dashboard_state_fields_required')
        if value['event_type'] not in ('Wedding','Corporate'):raise ValueError('unsupported_event_type')
        iso(value['event_date'])
        for field in FIELDS-{'event_type','event_date','quotes','removed_quote_ids'}:
            v=value[field]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('finite_number_required:'+field)
        if type(value['guests']) is not int:raise ValueError('integer_guest_count_required')
        for field in ('venue_width_m','venue_length_m'):
            if not 0<value[field]<=10000:raise ValueError('invalid_venue_dimension:'+field)
        p=defaults(self.planner.service.config,value['event_type'])
        for field in ('guests','event_hours','target_budget_lkr','retained_receipts_lkr','min_profit_margin_pct'):p[field]=value[field]
        p.update(stage_width_m=4.,stage_length_m=6.,venue_area_m2=value['venue_width_m']*value['venue_length_m'])
        return {'planning_inputs':p,'event_date':value['event_date'],
                'quotes':deepcopy(value['quotes']),'removed_quote_ids':deepcopy(value['removed_quote_ids'])}

    def calculate(self,payload):
        if not isinstance(payload,dict) or set(payload)!={'baseline','alternative'}:raise ValueError('exact_comparison_fields_required')
        response=self.planner.request({k:self.state(payload[k]) for k in ('baseline','alternative')})
        for key in ('baseline','alternative'):
            r=response[key]
            service=self.planner.service
            if hasattr(service,'disclosure'):
                r['calculator_scope']=service.disclosure(self.state(payload[key])['planning_inputs'])
                if r['status']=='calculated' and r['calculator_scope']['extended_input_fields']:
                    r['plan']['warnings'].append(r['calculator_scope']['statement'])
            if r['status']=='calculated':
                p=r['plan']
                if abs(sum(p['line_items_lkr'].values())-p['total_cost_lkr'])>.011:raise RuntimeError('response_ledger_does_not_reconcile')
                if not all(math.isfinite(p[n]) for n in ('total_cost_lkr','expected_profit_lkr','expected_margin_pct')):raise RuntimeError('invalid_calculation_response')
                source=payload[key]
                area=source['venue_width_m']*source['venue_length_m']
                assumptions=self.planner.service.config['assumptions']
                r['geometry']={'venue_width_m':source['venue_width_m'],'venue_length_m':source['venue_length_m'],
                    'venue_area_m2':area,'guests_per_m2':source['guests']/area,
                    'area_rule_capacity':max(0,math.floor((area-24-assumptions['fixed_service_circulation_area_m2'])/assumptions['seat_area_m2']))}
            if self.risk:self.risk.apply(self.state(payload[key]),r)
            from .lkr_graph_inference import graph_result
            r['graph_risk']=graph_result(self.state(payload[key]),r)
        if self.risk:
            response['provenance'].update(model_run=self.risk.run_id,risk_design_sha256=self.risk.metadata['design_sha256'])
        if hasattr(self.planner.service,'scope'):
            response['provenance'].update(calculator_scope_version=self.planner.service.scope['version'],
                base_configuration_sha256=self.planner.service.base_config_hash,
                calculator_scope_sha256=self.planner.service.config['planner_runtime_scope']['scope_file_sha256'])
        response.update(api_version='lkr-dashboard.0.1',mode='research_only',report_text=report_text(response))
        response['insights']=insights(response,payload)
        response['report_text']+=insight_report(response['insights'])
        graph=response['alternative']['graph_risk']
        response['report_text']+='\nLKR GRAPH MODEL / EXPLORATORY COMPARATOR\n'+json_graph_report(graph)
        response['pricing_scope']={k:pricing_disclosure(payload[k],response[k]) for k in ('baseline','alternative')}
        response['report_text']+='\nPRICE SCOPE / NO CALIBRATED EVENT-DATE FORECAST\n'+response['pricing_scope']['alternative']['statement']+'\n'
        for line in response['pricing_scope']['alternative']['lines']:
            response['report_text']+=f"{line['line_key']}: {line['basis']}; charge scope {line['tax_scope']}; future-price terms {line['price_terms']}; declared increase {line['documented_increase_pct']}; independently verified: no\n"
        for target, drivers in (response['alternative'].get('shap_drivers') or {}).items():
            if drivers:
                response['report_text']+='\nNATIVE TREESHAP: '+target+' (log-odds, not monetary effects)\n'
                for d in drivers:
                    response['report_text']+=f"{d['feature']}: {d['contribution_log_odds']:+.6f} log-odds\n"
        if self.risk and hasattr(self.risk,'evaluation'):
            evaluation=self.risk.evaluation
            response['report_text']+='\nMODEL EVALUATION — SYNTHETIC ENGINEERING EXPERIMENT\nRun: '+self.risk.run_id+'\n'
            response['report_text']+=evaluation['selection']+'\n'+evaluation['test_scope']+'\n'
            for target,value in evaluation['targets'].items():
                current=value['test']['xgboost'];previous=value['test']['original_v3']
                response['report_text']+=f"{target}: nested CV accuracy {value['nested_cv']['oof_metrics']['accuracy']:.6f}; existing test accuracy {current['accuracy']:.6f}; prior v3 accuracy {previous['accuracy']:.6f}; rule accuracy {value['test']['planning_rule_class_accuracy']:.6f}; recall {current['recall']:.6f}; log-loss {current['log_loss']:.6f}\n"
            response['report_text']+='No observed-event validation, calibrated real-world probabilities or established superiority over financial rules.\n'
        return response


def json_graph_report(graph):
    import json
    return json.dumps(graph,indent=2,allow_nan=False)+'\nGraph scores do not set the rule-based health indicator and are not CAD or real-world validated probabilities.\n'
