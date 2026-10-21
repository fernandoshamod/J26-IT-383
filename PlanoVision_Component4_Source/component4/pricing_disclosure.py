"""Describe existing calculation scope without modifying frozen financial rules."""


def pricing_disclosure(state, result):
    plan=result.get('plan')
    quotes=[q for q in state['quotes'] if q['id'] not in state['removed_quote_ids']]
    lines=[]
    for key, amount in (plan or {}).get('line_items_lkr',{}).items():
        quote=next((q for q in quotes if (q['service'] if q['mode']=='replace' else 'extra:'+q['id'])==key),None)
        if quote:
            lines.append({'line_key':key,'amount_lkr':amount,'basis':quote['source_kind'],
                'tax_scope':quote['tax_scope'],'price_terms':quote['pricing_policy'],
                'documented_increase_pct':quote['increase_pct'],'evidence_ref':quote['evidence_ref'],
                'independently_verified':False})
        else:
            cancellation=key.startswith('cancellation:')
            lines.append({'line_key':key,'amount_lkr':amount,
                'basis':'declared_cancellation_charge' if cancellation else 'reference_plus_experimental_assumptions',
                'tax_scope':'declared_cancellation_total' if cancellation else 'reference_or_assumed_not_supplier_verified',
                'price_terms':'declared_cancellation_total' if cancellation else 'no_calibrated_date_forecast',
                'documented_increase_pct':None,'evidence_ref':'Existing engine configuration; not a confirmed current quotation',
                'independently_verified':False})
    return {'event_date':state['event_date'],'calibrated_future_forecast_applied':False,
            'entire_event_supplier_verified':False,'lines':lines,
            'statement':'Event date alone does not forecast price increases. Reference costs and planner allowances are estimates. Only declared quote price locks or explicit total escalation percentages are applied to those quoted lines; remaining costs are not forecast to the event date. Supplier declarations are not independently verified. Client-output tax is excluded from the retained-payment price guide.'}
