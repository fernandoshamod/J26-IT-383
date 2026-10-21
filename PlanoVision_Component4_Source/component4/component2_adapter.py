"""Component 2 -> Component 4 declared quotation contract. No lookup or approvals."""
from copy import deepcopy
import json
from .planner_services import QFIELDS, iso, text, validate_quote

VERSION='component2.quotation_bundle.v1'
ENVELOPE={'contract_version','bundle_id','supplier_id','issued_on','event_type','event_date','quotations'}


def strict_json(value):
    if not isinstance(value,str) or len(value.encode('utf-8'))>60000:raise ValueError('bounded_bundle_json_required')
    def pairs(items):
        result={}
        for key,item in items:
            if key in result:raise ValueError('duplicate_bundle_key')
            result[key]=item
        return result
    return json.loads(value,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_bundle_value')))


def import_bundle(bundle, state):
    if not isinstance(bundle,dict) or set(bundle)!=ENVELOPE or bundle['contract_version']!=VERSION:
        raise ValueError('exact_component2_bundle_contract_required')
    for key in ('bundle_id','supplier_id'):text(bundle[key],key)
    iso(bundle['issued_on']);iso(bundle['event_date'])
    if bundle['issued_on']>bundle['event_date']:raise ValueError('quote_issued_after_event')
    if bundle['event_type']!=state['event_type'] or bundle['event_date']!=state['event_date']:
        raise ValueError('component2_event_scope_mismatch')
    lines=bundle['quotations']
    if not isinstance(lines,list) or not 1<=len(lines)<=30 or len(lines)+len(state['quotes'])>30:
        raise ValueError('invalid_component2_quote_count')
    if not isinstance(state['quotes'],list) or not isinstance(state['removed_quote_ids'],list):raise ValueError('invalid_current_quote_state')
    for q in state['quotes']:validate_quote(q)
    proposed=deepcopy(state);ids={q['id'] for q in proposed['quotes']}
    if len(ids)!=len(proposed['quotes']) or any(not isinstance(i,str) or i not in ids for i in state['removed_quote_ids']) or len(set(state['removed_quote_ids']))!=len(state['removed_quote_ids']):
        raise ValueError('invalid_current_quote_ids')
    for line in lines:
        if not isinstance(line,dict) or set(line)!=((QFIELDS-{'source_kind'})|{'currency'}):
            raise ValueError('exact_component2_quote_fields_required')
        if line['currency']!='LKR':raise ValueError('component2_currency_must_be_LKR_no_implicit_fx')
        text(line['evidence_ref'],'evidence_ref')
        if line['pricing_policy']=='planning_estimate':raise ValueError('component2_quote_is_not_a_planner_allowance')
        q={k:deepcopy(v) for k,v in line.items() if k!='currency'}
        q['source_kind']='user_supplied_unverified_quote'
        q['evidence_ref']=f"Component 2 bundle {bundle['bundle_id']} / supplier {bundle['supplier_id']}: {q['evidence_ref']}"
        validate_quote(q)
        if q['id'] in ids:raise ValueError('component2_duplicate_quote_id_no_silent_overwrite')
        ids.add(q['id']);proposed['quotes'].append(q)
    return {'contract_version':VERSION,'status':'proposed_inputs_only','proposed_state':proposed,
            'source_component':2,'bundle_id':bundle['bundle_id'],'supplier_id':bundle['supplier_id'],
            'transport_authenticated':False,'independently_verified':False,
            'warnings':['Imported declarations, not independent verification or institutional approval.',
                        'Preview must pass existing financial/quotation checks. Main plan is not changed until confirmation.',
                        'Missing tax, validity or future-price terms remain blocking; no live lookup or FX conversion occurred.']}
