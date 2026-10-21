"""Interactive add/remove services and grounded report using versioned pricing inputs."""
from copy import deepcopy
from datetime import datetime,timezone
import argparse
import json
import math
from pathlib import Path
import sys
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.planner_services import PlannerServices,CORE,CORE_BASES,BASES,report_text,validate_quote,iso
from component4.lkr_research import defaults
from component4.release_input import assert_experiment_output
from component4.planner_input import collect_planner_inputs


def numeric(prompt,*,nullable=False,lo=0,hi=None):
    while True:
        raw=input(prompt).strip().replace(',','')
        if not raw and nullable:return None
        try:
            v=float(raw)
            if not math.isfinite(v) or v<lo or (hi is not None and v>hi):raise ValueError()
            return v
        except ValueError:print('Enter a valid number; unknown values stay missing, never zero by default.')


def get_date(prompt,default):
    while True:
        value=input(prompt+f' [{default}]: ').strip() or default
        try:iso(value);return value
        except ValueError:print('Use YYYY-MM-DD.')


def read_quote(state,mode):
    qid='quote_'+uuid4().hex[:8]
    if mode=='replace':
        service=input('Core service to replace ('+', '.join(sorted(CORE))+'): ').strip().lower()
        if service not in CORE:raise ValueError('unsupported_core_service')
        basis=CORE_BASES[service]
    else:
        service=input('Optional service identifier (e.g. photography, lighting, transport): ').strip().lower()
        basis=input('Quantity basis ('+', '.join(sorted(BASES))+') [booking]: ').strip() or 'booking'
    label=input('Service label: ').strip() or service
    rate=numeric('Quoted unit price in LKR (blank = quotation required): ',nullable=True)
    scope=input('Charge scope: all_in / exclusive_declared / unknown [unknown]: ').strip() or 'unknown'
    if scope=='all_in':service_pct=tax_pct=0
    elif scope=='exclusive_declared':
        service_pct=numeric('Service charge % from quote (blank = unknown): ',nullable=True,hi=100)
        tax_pct=numeric('Tax % from quote (blank = unknown): ',nullable=True,hi=100)
    else:service_pct=tax_pct=None
    policy=input('Future price terms: locked / documented_escalation / unknown [unknown]: ').strip() or 'unknown'
    increase=0 if policy=='locked' else numeric('Documented price change % (blank = unknown): ',nullable=True,lo=-99,hi=500) if policy=='documented_escalation' else None
    reference=input('Quote/source reference (no private client details): ').strip()
    start=get_date('Quote valid from',state['event_date']);until=get_date('Quote valid until',state['event_date'])
    committed=input('Already committed/contracted? y/N: ').strip().lower()=='y'
    fee=numeric('Confirmed ALL-IN cancellation fee LKR (blank = unknown): ',nullable=True) if committed else 0
    covers=[service] if mode=='replace' else [s.strip() for s in input(f'Included service identifiers [{service}]: ').strip().split(',') if s.strip()]
    q={'id':qid,'label':label,'mode':mode,'service':service,'quantity_basis':basis,'unit_rate_lkr':rate,
       'tax_scope':scope,'service_pct':service_pct,'tax_pct':tax_pct,'pricing_policy':policy,'increase_pct':increase,
       'source_kind':'user_supplied_unverified_quote','evidence_ref':reference,'valid_from':start,'valid_until':until,
       'covers':covers or [service],'committed':committed,'cancellation_fee_lkr':fee}
    validate_quote(q);return q


def save(response):
    folder=assert_experiment_output(ROOT/'outputs/planner_service_reports');folder.mkdir(parents=True,exist_ok=True)
    basename=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    with (folder/(basename+'.json')).open('x',encoding='utf-8') as f:json.dump(response,f,indent=2,allow_nan=False)
    with (folder/(basename+'.txt')).open('x',encoding='utf-8') as f:f.write(report_text(response))
    print('Saved readable report:',folder/(basename+'.txt'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--example',action='store_true');parser.add_argument('--no-save',action='store_true')
    args=parser.parse_args();planner=PlannerServices()
    if args.example:
        payload=json.loads((ROOT/'fixtures/planner_services.mock_test_only.json').read_text())
        response=planner.request(payload);print(report_text(response))
        if not args.no_save:save(response)
        return
    print('Planner services: add/remove optional services, replace Wedding rates, and export readable reports.')
    print('Original base costs retain research assumptions; supplied quotations are declared, not independently verified.')
    try:
        choice=input('Event 1=Wedding / 2=Corporate [1]: ').strip()
        if choice not in ('','1','2'):raise ValueError('choose_Wedding_or_Corporate')
        event='Corporate' if choice=='2' else 'Wedding'
        while True:
            try:
                inputs,venue_dimensions=collect_planner_inputs(planner.service.config,event)
                break
            except ValueError as exc:
                print('Cannot use these venue dimensions:',exc)
        baseline={'planning_inputs':inputs,'event_date':get_date('Event date','2026-10-22'),
                  'quotes':[],'removed_quote_ids':[]}
        alternative=deepcopy(baseline)
        while True:
            action=input('\nAction: a=add optional quote, p=replace core rate, r=remove quote, c=change event inputs, e=change event date, b=set current as baseline, v=view/save comparison, q=quit: ').strip().lower()
            if action=='q':return
            try:
                if action in ('a','p'):
                    alternative['quotes'].append(read_quote(alternative,'replace' if action=='p' else 'add'))
                    print('Quote stored; use v to calculate.')
                elif action=='r':
                    for q in alternative['quotes']:print(q['id'],q['label'],'removed' if q['id'] in alternative['removed_quote_ids'] else 'active')
                    qid=input('Quote ID to remove: ').strip()
                    if qid not in {q['id'] for q in alternative['quotes']}:raise ValueError('unknown_quote_id')
                    if qid not in alternative['removed_quote_ids']:alternative['removed_quote_ids'].append(qid)
                elif action=='c':
                    inputs,dimensions=collect_planner_inputs(planner.service.config,event,alternative['planning_inputs'],venue_dimensions)
                    alternative['planning_inputs']=inputs
                    venue_dimensions=dimensions
                elif action=='e':alternative['event_date']=get_date('Event date',alternative['event_date'])
                elif action=='b':
                    response=planner.request({'baseline':alternative,'alternative':alternative})
                    if response['alternative']['status']!='calculated':print('Cannot accept an unpriced/blocked baseline.');continue
                    baseline=deepcopy(alternative);print('Baseline updated for future comparisons.')
                elif action=='v':
                    response=planner.request({'baseline':baseline,'alternative':alternative})
                    print(report_text(response))
                    if not args.no_save:save(response)
                else:print('Choose a, p, r, c, e, b, v or q.')
            except ValueError as exc:print('Cannot apply:',exc)
    except (KeyboardInterrupt,EOFError):print('\nClosed without changing models/datasets.')


if __name__=='__main__':main()
