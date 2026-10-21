"""Generate the proposed transport schema and an explicitly test-only example."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import json
from component4.planner_services import QFIELDS,BASES,CORE


def main():
    string={'type':'string','minLength':1,'maxLength':1000}
    numeric=lambda low=0,high=1e15:{'type':['number','null'],'minimum':low,'maximum':high}
    fields={k:dict(string) for k in QFIELDS-{'source_kind'}}
    fields.update(id={'type':'string','pattern':'^[A-Za-z0-9_-]{1,64}$'},mode={'enum':['add','replace']},
        quantity_basis={'enum':sorted(BASES)},currency={'const':'LKR'},
        unit_rate_lkr=numeric(0,1e12),tax_scope={'enum':['all_in','exclusive_declared','unknown']},
        service_pct=numeric(0,100),tax_pct=numeric(0,100),
        pricing_policy={'enum':['locked','documented_escalation','unknown']},increase_pct=numeric(-99,500),
        valid_from={'type':'string','format':'date'},valid_until={'type':'string','format':'date'},
        covers={'type':'array','minItems':1,'uniqueItems':True,'items':string},
        committed={'type':'boolean'},cancellation_fee_lkr=numeric())
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Proposed Component 2 quotation bundle v1',
        'type':'object','additionalProperties':False,
        'description':'Local declared-input adapter; not authenticated integration or independent verification. Backend additionally checks units, inclusions, dates and all-in/double-charge invariants.',
        'required':['contract_version','bundle_id','supplier_id','issued_on','event_type','event_date','quotations'],
        'properties':{'contract_version':{'const':'component2.quotation_bundle.v1'},'bundle_id':string,'supplier_id':string,
            'issued_on':{'type':'string','format':'date'},'event_date':{'type':'string','format':'date'},
            'event_type':{'enum':['Wedding','Corporate']},'quotations':{'type':'array','minItems':1,'maxItems':30,
                'items':{'type':'object','additionalProperties':False,'required':sorted(fields),'properties':fields}}}}
    (ROOT/'api/contracts/component2_quotation_bundle.schema.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
    example={'contract_version':'component2.quotation_bundle.v1','bundle_id':'MOCK-TEST-BUNDLE-001',
        'supplier_id':'MOCK-NOT-A-REAL-SUPPLIER','issued_on':'2026-10-18','event_type':'Wedding','event_date':'2026-10-22',
        'quotations':[{'id':'mock_p2_photo','label':'MOCK TEST photography — not a real quotation','mode':'add',
            'service':'photography','quantity_basis':'booking','currency':'LKR','unit_rate_lkr':10000,
            'tax_scope':'exclusive_declared','service_pct':10,'tax_pct':18,'pricing_policy':'documented_escalation',
            'increase_pct':10,'evidence_ref':'MOCK TEST ONLY: all rates and percentages are illustrative, not market/tax evidence',
            'valid_from':'2026-10-18','valid_until':'2026-11-01','covers':['photography'],'committed':False,'cancellation_fee_lkr':0}]}
    (ROOT/'fixtures/component2_quotation_bundle.mock_test_only.json').write_text(json.dumps(example,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Proposed schema and clearly marked test-only example created; no approval or supplier evidence created.')


if __name__=='__main__':main()
