"""Focused new contract checks; no optimization or repeated comparative evidence."""
from io_context import *
from recovery import check_request,request_hash
import copy
def main():
    protocol=read(H/'FROZEN_PROTOCOL.json');cases=[r['request'] for r in protocol['requests']];checks=[]
    checks.append({'name':'all_36_frozen_requests_still_admitted','passed':all(check_request(r) for r in cases)})
    for kind in ['guests','functions','nonfinite']:
        r=copy.deepcopy(cases[0])
        if kind=='guests':r['core']['client']['guests']=r['core']['planner']['guests']=40
        if kind=='functions':r['core']['required_functions']=['dining']
        if kind=='nonfinite':r['domains']['dance_area_m2'].append(float('inf'))
        # Nonfinite inputs must be rejected without trying to hash or bless them.
        try:check_request(r)
        except ValueError as e:checks.append({'name':'reject_'+kind,'passed':True,'reason':str(e)})
        else:checks.append({'name':'reject_'+kind,'passed':False})
    assert all(q['passed'] for q in checks),checks
    save(H/'ADMISSION_SUPPLEMENT.json',{'status':'PASS','checks':checks,'total':len(checks),'optimizer_evaluations':0,'scope':'four additional checks; original benchmark and 56-test evidence unchanged'})
    print('PASS',len(checks),'focused admission checks; zero evaluations')
if __name__=='__main__':main()
