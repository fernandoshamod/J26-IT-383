"""Transparent planning-score decomposition and grounded recommendations; no LLM."""
from .planner_services import cash


def insights(response, payload):
    result=response['alternative'];plan=result['plan']
    if result['status']!='calculated' or plan is None:
        return {'status':'unavailable','score':None,'recommendations':[],
                'reason':'Resolve blocked or unpriced inputs before scoring.',
                'explainability':{'method':'unavailable','drivers':[]}}
    state=payload['alternative'];cost=plan['total_cost_lkr'];reserve=plan['reserve_lkr']
    budget=state['target_budget_lkr'];receipts=state['retained_receipts_lkr'];minimum=state['min_profit_margin_pct']
    margin=plan['expected_margin_pct']
    budget_cover=min(1,budget/(cost+reserve)) if cost+reserve>0 else 1
    margin_cover=min(1,max(0,margin/minimum)) if minimum>0 else float(margin>=0)
    score=100*min(budget_cover,margin_cover)
    if not 0<=score<=100 or (plan['expected_profit_lkr']<0 and score!=0):
        raise RuntimeError('invalid_planning_score_or_loss_not_zero')
    existing=result.get('draft_planning_health')
    if existing is None or abs(existing['score_points']-score)>1e-6:raise RuntimeError('health_formula_disagreement')
    recommendations=[]
    def add(kind,title,amount,rationale):
        recommendations.append({'id':kind,'title':title,'amount_lkr':amount,'rationale':rationale,
                                'method':'deterministic_policy_calculation','automatic_action':False})
    if not plan['affordable_after_reserve']:
        add('budget_shortfall','Obtain a higher cost allowance or reduce quoted costs',
            cash(cost+reserve-budget),'Amount needed to cover modeled cost plus earmarked reserve; raising the budget does not raise profit.')
    if not plan['margin_feasible']:
        add('client_payment','Discuss a revised client quote',cash(max(0,cost/(1-minimum/100)-receipts)),
            'Additional retained client payment needed for the minimum margin at unchanged modeled cost. Excludes output tax and requires client agreement.')
    reserve_ratio=reserve/cost if cost else 0
    allowed=min(budget/(1+reserve_ratio),receipts*(1-minimum/100))
    reduction=cash(max(0,cost-allowed))
    if reduction>0:
        add('cost_reduction','Seek documented cost reductions',reduction,
            'Required modeled cost reduction to meet both budget-with-reserve and minimum-margin rules at unchanged client payment. Savings require actual requotation.')
    if not recommendations:
        add('retain_headroom','Current plan meets the modeled financial rules',None,
            'Keep the earmarked reserve, verify supplier inclusions/taxes and obtain written price terms. This does not guarantee a profitable outcome.')
    add('conservative_client_quote','Review reserve-inclusive client-price guide',
        cash(max(0,plan['recommended_client_price_excluding_output_tax_lkr']-receipts)),
        'Additional retained payment relative to the separate conservative guide (cost + reserve)/(1 − minimum margin). Reserve is not a second accounting expense.')
    delta=response.get('delta')
    drivers=[] if delta is None else [{'line_item':key,'change_lkr':value} for key,value in
        sorted(delta['line_changes_lkr'].items(),key=lambda item:-abs(item[1])) if value!=0]
    shap=result.get('shap_drivers')
    has_shap=bool(shap and any(shap.values()))
    return {'status':'calculated','score':{'name':'Experimental financial planning coverage',
            'value':score,'unit':'points_out_of_100','validated':False,
            'status':'within_modelled_rules' if plan['affordable_after_reserve'] and plan['margin_feasible'] else 'action_required',
            'formula':'100 × min(budget_coverage, margin_coverage)',
            'budget_coverage':budget_cover,'margin_coverage':margin_cover,
            'budget_formula':'min(1, budget / (estimated_cost + reserve)); zero cost + reserve gives 1',
            'margin_formula':'min(1, max(0, expected_margin_pct / minimum_margin_pct)); if minimum = 0, use 1 for nonnegative margin, otherwise 0',
            'limitation':'Not a validated financial health score, probability of safety or calibrated ML output. Capacity is a separate mandatory check.'},
            'recommendations':recommendations,
            'explainability':{'method':'native_TreeSHAP_plus_ledger_delta' if has_shap else 'ledger_delta_only',
                'model_explanation_available':has_shap,'drivers':drivers,
                'model_explanation_note':'TreeSHAP explains supported classifier log-odds, not rupee savings. When scores are withheld, no SHAP explanation is fabricated.'}}


def insight_report(value):
    if value['status']!='calculated':return '\nPLANNING SCORE / EXPLANATIONS\nUnavailable: '+value['reason']+'\n'
    s=value['score']
    lines=['','EXPERIMENTAL FINANCIAL PLANNING COVERAGE',f"Score: {s['value']:.2f}/100; status: {s['status']}",
           'Formula: '+s['formula'],f"Budget coverage: {s['budget_coverage']:.6f}; margin coverage: {s['margin_coverage']:.6f}",
           s['budget_formula'],s['margin_formula'],s['limitation'],'','RECOMMENDATIONS (POLICY RULES, NOT ML OR LLM ADVICE)']
    for item in value['recommendations']:
        amount='' if item['amount_lkr'] is None else f" — LKR {item['amount_lkr']:,.2f}"
        lines.extend([item['title']+amount,item['rationale']])
    lines.extend(['','EXPLANATION OF COST CHANGES (ACCOUNTING, NOT SHAP)'])
    for d in value['explainability']['drivers']:lines.append(f"{d['line_item']}: LKR {d['change_lkr']:+,.2f}")
    lines.append(value['explainability']['model_explanation_note'])
    return '\n'.join(lines)+'\n'
