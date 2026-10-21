"""Local CLI. All outputs isolated; no HTTP route or frontend changes."""
import argparse,sys
from common import *
from compiler import compile_scene
from baseline import baseline_scene
from oracle import validate_spec,validate_result
from fixtures import fixture
from bridge import execute

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['compile','run','demo']);p.add_argument('--input');p.add_argument('--out',required=True);p.add_argument('--policy');p.add_argument('--baseline',action='store_true');p.add_argument('--partial',action='store_true');p.add_argument('--dance',action='store_true');p.add_argument('--seed',type=int,default=20261017);a=p.parse_args()
    out=(HERE/a.out).resolve()
    if not out.is_relative_to(HERE) or out.exists():raise ValueError('USE_NEW_ISOLATED_OUTPUT_DIRECTORY')
    policy=read(a.policy) if a.policy else read(HERE/'profiles.json')
    if a.command=='demo':
        out.mkdir(parents=True);request=fixture(out/'inputs',partial=a.partial,optional=['dancing'] if a.dance else []);dest=out/'execution'
    else:
        if not a.input:raise ValueError('INPUT_JSON_REQUIRED')
        request=read(a.input);dest=out
    spec=(baseline_scene if a.baseline else compile_scene)(request,policy)
    if a.command=='compile':
        dest.mkdir(parents=True,exist_ok=False);save(dest/'REQUEST.json',request);save(dest/'SPEC.json',spec);save(dest/'POLICY.json',policy)
        v=validate_spec(request,spec,policy,spec['status']);save(dest/'INDEPENDENT_SPEC_CHECK.json',v)
        status=spec['status'];print(__import__('json').dumps(dict(status=status,spec_sha256=spec['spec_sha256'],quantities=spec['required_quantities'],issues=spec['issues'],independent_valid=v['valid']),indent=2));return 0 if status=='accepted' and v['valid'] else 2
    response=execute(request,spec,dest,seed=a.seed,policy=policy);v=validate_result(request,spec,response);save(dest/'INDEPENDENT_RESULT.json',v)
    print(__import__('json').dumps(dict(status=response['status'],reason=response['reason'],candidates=len(response['candidate_layouts']),selected=response['selected_ids'],evaluations=response['optimizer_evaluations'],independent_valid=v['valid']),indent=2));return 0 if response['status']=='success' and v['valid'] else 2

if __name__=='__main__':raise SystemExit(main())
