"""Opt-in draft planning indicator and post-invoice rate comparison.

Neither is trained, calibrated, a fraud detector, or an approval mechanism.
No frozen dataset or prediction-time feature is modified.
"""
from datetime import date
import math


def number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('finite_number_required:' + name)
    if value < 0 or (positive and value == 0):
        raise ValueError('invalid_nonnegative_value:' + name)
    return value


def planning_indicator(result):
    """Bottleneck coverage, not weighted health, probability or MC output."""
    policy = {'version':'planning-coverage.draft.0.1', 'approval_status':'proposed_not_formally_approved',
              'empirically_validated':False, 'origin':'experimental_deterministic_policy_not_ML',
              'formula':'100 * min(1, budget/(planned_cost+reserve), max(0, margin_points/minimum_margin_points))',
              'interpretation':'100 means both proposed planning thresholds met, not financial safety',
              'unit':'experimental_points_0_to_100'}
    output = {'policy':policy, 'status':'unavailable', 'score':None, 'components':None,
              'reason':None, 'real_world_financial_health_score':None}
    if result['status'] != 'calculated':
        output['reason']='configuration_blocked'; return output
    plan = result['planned']
    cost = number(plan['total_cost_score'], 'cost')
    reserve = number(plan['reserve_score'], 'reserve')
    budget = number(result['inputs']['budget_score'], 'budget', positive=True)
    minimum = number(plan['required_min_margin_points'], 'minimum_margin', positive=True)
    margin = plan['expected_margin_points']
    if margin is None or not math.isfinite(margin):
        output['reason']='undefined_margin'; return output
    budget_coverage = min(1., budget/(cost+reserve)) if cost+reserve > 0 else 1.
    margin_coverage = min(1., max(0., margin/minimum))
    output.update(status='experimental', score=100*min(budget_coverage, margin_coverage),
                  components={'budget_and_earmarked_reserve_coverage':budget_coverage,
                              'minimum_margin_coverage':margin_coverage})
    return output


def health_request(research, payload):
    decision = research.request(payload, 'calculate')
    return {'api_version':'experimental-indicators.0.1', 'operation':'planning-health',
            'decision':decision, 'indicator':planning_indicator(decision['result'])}


FIELDS = {'line_id','service','unit','currency','quantity','unit_rate','date',
          'tax_scope','included_services','bundle_id','evidence_reference'}


def snapshot(lines):
    if not isinstance(lines, list) or not 1 <= len(lines) <= 30:
        raise ValueError('one_to_thirty_line_items_required')
    mapped = {}
    for line in lines:
        if not isinstance(line, dict) or set(line) != FIELDS:
            raise ValueError('exact_quote_invoice_fields_required')
        for key in FIELDS-{'quantity','unit_rate','included_services','bundle_id'}:
            if not isinstance(line[key], str) or not line[key].strip():
                raise ValueError('nonempty_string_required:'+key)
        if line['line_id'] in mapped:
            raise ValueError('duplicate_line_id')
        number(line['quantity'], 'quantity', positive=True)
        number(line['unit_rate'], 'unit_rate')
        try:
            if date.fromisoformat(line['date']).isoformat()!=line['date']: raise ValueError()
        except ValueError:
            raise ValueError('iso_date_required') from None
        if line['bundle_id'] is not None and (not isinstance(line['bundle_id'],str) or not line['bundle_id'].strip()):
            raise ValueError('invalid_bundle_id')
        services = line['included_services']
        if not isinstance(services,list) or not services or any(not isinstance(s,str) or not s.strip() for s in services) or len(set(services))!=len(services):
            raise ValueError('unique_included_services_required')
        mapped[line['line_id']] = line
    # A package plus separately billed included component cannot be reconciled automatically.
    claimed = set()
    for line in lines:
        if claimed & set(line['included_services']):
            raise ValueError('overlapping_included_services_require_manual_review')
        claimed.update(line['included_services'])
    return mapped


def invoice_request(payload):
    if not isinstance(payload,dict) or set(payload)!={'quote','invoice','relative_rate_tolerance','evidence_kind'}:
        raise ValueError('exact_comparison_fields_required')
    if payload['evidence_kind'] not in ('mock_test_only','user_supplied_unverified'):
        raise ValueError('unsupported_evidence_kind')
    tolerance = number(payload['relative_rate_tolerance'], 'relative_rate_tolerance')
    if tolerance > 1: raise ValueError('tolerance_must_be_between_zero_and_one')
    quote, invoice = snapshot(payload['quote']), snapshot(payload['invoice'])
    comparisons = []
    for line_id in sorted(set(quote)|set(invoice)):
        q, i = quote.get(line_id), invoice.get(line_id)
        row = {'line_id':line_id,'status':'manual_review','rate_increase_flag':None,
               'relative_rate_change':None,'rate_effect_amount':None,'quantity_effect_amount':None,
               'total_difference_amount':None,'currency':None,'reasons':[]}
        if q is None or i is None:
            row['reasons']=['unmatched_quote_or_invoice_line']
        else:
            row['currency']=q['currency']
            for key in ('service','unit','currency','tax_scope','bundle_id'):
                if q[key]!=i[key]:row['reasons'].append('scope_mismatch:'+key)
            if set(q['included_services'])!=set(i['included_services']):row['reasons'].append('scope_mismatch:included_services')
            if q['tax_scope'].lower() in ('unknown','unspecified'):row['reasons'].append('unknown_tax_scope')
            if i['date'] < q['date']:row['reasons'].append('invoice_precedes_quote')
            if not row['reasons']:
                # Exact decomposition: Qi*(Pi-Pq) + Pq*(Qi-Qq) = Qi*Pi-Qq*Pq.
                rate_effect = i['quantity']*(i['unit_rate']-q['unit_rate'])
                quantity_effect = q['unit_rate']*(i['quantity']-q['quantity'])
                delta = i['quantity']*i['unit_rate']-q['quantity']*q['unit_rate']
                if not all(math.isfinite(v) for v in (rate_effect,quantity_effect,delta)):
                    raise ValueError('comparison_arithmetic_overflow')
                row.update(status='comparable',rate_effect_amount=rate_effect,
                           quantity_effect_amount=quantity_effect,total_difference_amount=delta)
                if q['unit_rate']==0:
                    row['status']='manual_review'; row['reasons']=['zero_quote_rate_relative_change_undefined']
                else:
                    relative = (i['unit_rate']-q['unit_rate'])/q['unit_rate']
                    if not math.isfinite(relative): raise ValueError('comparison_arithmetic_overflow')
                    row.update(relative_rate_change=relative,rate_increase_flag=relative>tolerance+1e-12)
        comparisons.append(row)
    return {'api_version':'experimental-indicators.0.1','operation':'quote-invoice-comparison',
            'origin':'post_invoice_rule_comparison_not_prediction_or_fraud_proof',
            'evidence_kind':payload['evidence_kind'],'source_verified':False,
            'policy':{'relative_rate_tolerance':tolerance,'origin':'caller_selected_experimental_threshold_not_market_statistic'},
            'line_comparisons':comparisons,'Vendor_Cost_Anomaly_prediction':None,
            'warnings':['Not an input to planning-time risk models.',
                        'Scope matches are declared, not independently verified; review quote validity, contract changes and tax details.',
                        'No mixed-currency aggregation or automatic tax conversion.']}
