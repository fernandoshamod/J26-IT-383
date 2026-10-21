"""Optional local-only grounded narrative. Never calculates or updates finances."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import threading

ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.Lock()


class LLMUnavailable(RuntimeError):pass


def settings():
    d=json.loads((ROOT/'config/llm_report.v0.1.json').read_text())
    d['model']=os.environ.get('PLANOVISION_LLM_MODEL',d['model'])
    if d['provider']!='ollama_local' or d['host']!='127.0.0.1' or d['port']!=11434 or d['allow_cloud'] is not False or d['allow_automatic_model_pull'] is not False:
        raise ValueError('only_fixed_loopback_local_llm_is_supported')
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',d['model']) or 'cloud' in d['model'].lower():raise ValueError('local_installed_model_required_no_cloud')
    return d


def local_request(method,path,payload=None,timeout=3):
    connection=http.client.HTTPConnection('127.0.0.1',11434,timeout=timeout)
    try:
        body=None if payload is None else json.dumps(payload,allow_nan=False).encode()
        connection.request(method,path,body,{'Content-Type':'application/json'})
        response=connection.getresponse();raw=response.read(65537)
        if response.status!=200 or len(raw)>65536:raise LLMUnavailable('local_llm_http_error_or_response_too_large')
        return json.loads(raw)
    except (OSError,ValueError,http.client.HTTPException) as e:raise LLMUnavailable('local_ollama_unavailable_or_invalid_response') from e
    finally:connection.close()


def status():
    d=settings()
    result={'version':d['version'],'provider':'ollama_local','model':d['model'],'ready':False,
            'network_scope':'127.0.0.1:11434 only; no cloud fallback','reason':'local_model_not_installed_or_service_stopped'}
    try:
        tags=local_request('GET','/api/tags')
        model=next((m for m in tags.get('models',[]) if m.get('name')==d['model']),None)
        if model and not model.get('remote_host') and not model.get('remote_model') and isinstance(model.get('digest'),str) and model['digest']:
            if model['digest']!=d['expected_model_digest']:result.update(reason='local_model_digest_mismatch_review_configuration')
            else:result.update(ready=True,reason='installed_local_model',model_digest=model['digest'])
    except LLMUnavailable:pass
    return result


def engine_facts(comparison):
    a=comparison['alternative'];b=comparison['baseline']
    if a['status']!='calculated' or b['status']!='calculated':raise ValueError('valid_baseline_and_alternative_required_for_llm_report')
    p=a['plan'];delta=comparison['delta'];score=comparison['insights']['score']
    def amount(v):return f'LKR {v:,.2f}'
    facts=[{'id':'cost','statement':f"Estimated event expenses are {amount(p['total_cost_lkr'])}; these are research estimates, not confirmed supplier prices."},
           {'id':'profit','statement':f"Expected organizer {'loss' if p['expected_profit_lkr']<0 else 'profit'} is {amount(abs(p['expected_profit_lkr']))}; client payment is {amount(p['retained_receipts_lkr'])}."},
           {'id':'margin','statement':f"Expected net margin is {p['expected_margin_pct']:.2f} percent; the configured minimum-margin check {'passes' if p['margin_feasible'] else 'fails'}."},
           {'id':'budget','statement':f"Expense-budget check {'passes' if p['budget_feasible'] else 'fails'}; reserve-inclusive check {'passes' if p['affordable_after_reserve'] else 'fails'}. Reserve earmark is {amount(p['reserve_lkr'])}, not a second expense."},
           {'id':'change','statement':f"Compared with the original, cost changes by {amount(delta['cost_lkr'])} and expected profit by {amount(delta['profit_lkr'])}. This is a preview unless separately confirmed."},
           {'id':'health','statement':f"Rule-based planning indicator is {score['value']:.1f} of 100; this is not a trained-model probability or guarantee of safety."},
           {'id':'evidence','statement':'Risk models were evaluated on synthetic data, not independent completed-event financial outcomes. Monte Carlo shocks are hypothetical. No prediction guarantees profitability.'}]
    signals=[]
    for target,value in (a.get('model_scores') or {}).items():
        if value is not None:signals.append(f"{target}: uncalibrated XGBoost score {value['uncalibrated_score']:.4f}, class {value['class']}")
    for target,drivers in (a.get('shap_drivers') or {}).items():
        if drivers:
            top=drivers[0];signals.append(f"Native TreeSHAP {target}: {top['feature']} contributes {top['contribution_log_odds']:+.4f} log-odds, not rupee savings or causal effects")
    graph=a.get('graph_risk') or {}
    signals.append('LKR GAT comparator status: '+graph.get('status','unavailable')+'; not a CAD model or validated real-world probability')
    facts.append({'id':'model','statement':'; '.join(signals) if a.get('model_trace',{}).get('prediction_executed') else 'Saved risk predictions and TreeSHAP are withheld outside their training support; no model signal is substituted. '+signals[-1]})
    actions=[{'id':r['id'],'title':r['title'],'rationale':r['rationale']} for r in comparison['insights']['recommendations']]
    return facts,actions


def response_schema(facts):
    return {'type':'object','additionalProperties':False,'required':['explanations'],'properties':{
        'explanations':{'type':'array','minItems':len(facts),'maxItems':len(facts),'items':{'type':'object','additionalProperties':False,
            'required':['fact_id','text'],'properties':{'fact_id':{'type':'string','enum':[f['id'] for f in facts]},'text':{'type':'string','minLength':5,'maxLength':400,'pattern':'^[^0-9%$€£<>]*$'}}}},
        }}


def qualitative_facts(comparison):
    """Keep financial numbers out of generation; append authoritative amounts server-side."""
    p=comparison['alternative']['plan'];delta=comparison['delta']
    def direction(v):return 'increases' if v>0 else 'decreases' if v<0 else 'does not change'
    statements={
        'cost':'Event expenses are research estimates, not confirmed supplier quotations. Check supplier terms before committing.',
        'profit':'The current expected client payment results in an organizer '+('loss.' if p['expected_profit_lkr']<0 else 'profit.'),
        'margin':'The expected profit margin '+('meets' if p['margin_feasible'] else 'falls below')+' the configured minimum requirement.',
        'budget':'The expense budget check '+('passes' if p['budget_feasible'] else 'fails')+' and the reserve-inclusive check '+('passes' if p['affordable_after_reserve'] else 'fails')+'. Reserve is earmarked, not an additional accounting expense.',
        'change':'The preview '+direction(delta['cost_lkr'])+' estimated expenses and '+direction(delta['profit_lkr'])+' expected profit. The original plan changes only after separate confirmation.',
        'health':'The planning indicator summarizes rule-based budget and margin coverage; it is not a trained-model risk probability.',
        'evidence':'Model evaluation used synthetic scenarios, not independently observed completed events. Simulated shocks are hypothetical; findings require external validation.',
        'model':('Saved model signals are available. Native TreeSHAP describes feature contributions to model scores, not causal supplier savings. The graph model is a separate experimental comparator.'
                 if comparison['alternative'].get('model_trace',{}).get('prediction_executed') else 'Model signals and TreeSHAP are withheld outside their training support. No unavailable prediction is substituted.')}
    return [{'id':k,'statement':v} for k,v in statements.items()]


def validate_draft(draft,facts,actions):
    if not isinstance(draft,dict) or set(draft)!={'explanations'} or not isinstance(draft['explanations'],list):raise ValueError('invalid_llm_draft_schema')
    valid={f['id']:f for f in facts};seen=set()
    for p in draft['explanations']:
        if not isinstance(p,dict) or set(p)!={'fact_id','text'} or not isinstance(p['fact_id'],str) or p['fact_id'] not in valid or p['fact_id'] in seen:
            raise ValueError('unknown_duplicate_or_missing_llm_fact_reference')
        text=p['text']
        if not isinstance(text,str) or not 5<=len(text)<=400 or re.search(r'\d|[%$€£<>]|\b(?:LKR|guarantee\w*|risk.free|certified|approved|calibrated|certainly|always|never lose)\b',text,re.I):
            raise ValueError('llm_draft_contains_unapproved_numbers_markup_or_certainty_claim')
        seen.add(p['fact_id'])
    if seen!=set(valid):raise ValueError('critical_engine_facts_missing_from_llm_draft')
    return draft


def generate(comparison):
    facts,actions=engine_facts(comparison);d=settings();state=status()
    if not state['ready']:raise LLMUnavailable(state['reason'])
    if not LOCK.acquire(blocking=False):raise LLMUnavailable('local_llm_busy_try_again')
    try:
        schema=response_schema(facts)
        prompt={'authoritative_qualitative_facts':qualitative_facts(comparison),
                'required_output_schema':schema,
                'instruction':'Paraphrase each qualitative fact in plain English. Do not copy financial numbers; numerical engine facts will be appended by the server separately.'}
        request={'model':d['model'],'stream':False,'format':'json','keep_alive':'5m',
                 'options':{'temperature':0,'seed':d['seed'],'num_predict':900,'num_ctx':4096},
                 'messages':[{'role':'system','content':'Write short event-planning explanations. Return ONLY a JSON object with an explanations array, matching the supplied schema. Stop after that object. For each supplied fact provide exactly one short qualitative sentence. No digits, currency amounts, percentages or markup in sentences. Preserve the supplied meaning. Do not select recommendations, calculate finances or add claims.'},
                             {'role':'user','content':json.dumps(prompt,allow_nan=False)}]}
        response=local_request('POST','/api/chat',request,timeout=d['timeout_seconds'])
        if response.get('done') is not True or response.get('done_reason') not in (None,'stop') or response.get('model')!=d['model']:
            raise ValueError('incomplete_or_wrong_local_model_response')
        content=response.get('message',{}).get('content')
        if not isinstance(content,str) or len(content)>12000:raise ValueError('invalid_local_llm_content')
        draft=validate_draft(json.loads(content),facts,actions)
        # Recommendations are authoritative engine decisions, never LLM choices.
        draft['action_ids']=[a['id'] for a in actions[:3]]
        evidence=json.dumps({'facts':facts,'actions':actions},sort_keys=True,allow_nan=False).encode()
        result={'version':d['version'],'status':'generated_review_required','provider':'ollama_local',
                'model':d['model'],'model_digest':state['model_digest'],'engine_facts_sha256':hashlib.sha256(evidence).hexdigest(),
                'engine_facts':facts,'draft':draft,'selected_actions':[a for a in actions if a['id'] in draft['action_ids']],
                'financial_values_modified':False,'semantic_accuracy_independently_verified':False,
                'scope':'Local AI paraphrases require human review. All numerical facts and recommendations come from the engine; no plan, quotation or model score is changed.'}
        lines=['LOCAL LLM REPORT — REVIEW-REQUIRED DRAFT',result['scope'],f"Model: {d['model']} / digest {state['model_digest']}",'']
        byid={p['fact_id']:p['text'] for p in draft['explanations']}
        for f in facts:lines.extend([f['id'].upper(),f['statement'],'AI draft: '+byid[f['id']],''])
        for a in result['selected_actions']:lines.extend(['RULE-BASED ACTION: '+a['title'],a['rationale']])
        result['report_text']='\n'.join(lines);return result
    finally:LOCK.release()
