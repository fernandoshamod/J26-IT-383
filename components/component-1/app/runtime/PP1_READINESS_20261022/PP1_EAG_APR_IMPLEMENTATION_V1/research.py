"""Run a supplied controlled packet through actual governed research code."""
import argparse
from runtime import *
from eag_contracts import Packet
from models import Request
from repair import run

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--reference');p.add_argument('--method',choices=['FULL','INCREMENTAL','EAG'],default='EAG');p.add_argument('--seed',type=int,default=20261017);p.add_argument('--out',required=True);a=p.parse_args();out=(HERE/a.out).resolve()
    if not out.is_relative_to(HERE) or out.exists():raise ValueError('USE_NEW_ISOLATED_OUTPUT_DIRECTORY')
    packet=Packet.model_validate(read(a.input)).model_dump();Request.model_validate(packet['scene']);reference=read(a.reference) if a.reference else None
    response,graph=run(packet,out,a.method,a.seed,reference)
    print(__import__('json').dumps(dict(status=response['status'],operation=response['operation'],evaluations=response['optimizer_evaluations'],candidate_count=len(response['candidate_layouts']),menu=response['selected_ids'],certificate=response['certificate']['certificate_sha256'],reasons=response['reasons']),indent=2))
    return 0 if response['status']=='eligible' else 2
if __name__=='__main__':raise SystemExit(main())
