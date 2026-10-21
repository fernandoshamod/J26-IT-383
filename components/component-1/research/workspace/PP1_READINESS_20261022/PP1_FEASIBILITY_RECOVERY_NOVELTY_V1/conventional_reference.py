"""Independent declarative finite-domain baseline; does not call recovery enumerator/gates."""
from io_context import digest
import itertools

def enumerate_reference(r):
    keys=sorted(r['domains']);ops=r['operations'];found={}
    for values in itertools.product(*(r['domains'][k] for k in keys)):
        assignment=dict(zip(keys,values));changed={k for k in keys if assignment[k]!=r['requested'][k]}
        if changed&set(r['mandatory']):continue
        if assignment['dance_area_m2']<16 or assignment['minimum_buffets'] not in [1,2] or assignment['service_front_m']!=2.5*assignment['minimum_buffets']:continue
        # Find an authorized exact cover of the changed variables by declared operations.
        for n in range(1<<len(ops)):
            selected=[ops[j] for j in range(len(ops)) if n&(1<<j)]
            if any(o['id'] not in r['recovery_authority']['permitted_operations'] for o in selected):continue
            edits={};valid=True
            for o in selected:
                for k,to in o['to'].items():
                    if k in edits or r['requested'][k]!=o['from'][k] or assignment[k]!=to:valid=False
                    edits[k]=to
            if not valid or set(edits)!=changed:continue
            cost=sum(o['cost'] for o in selected);rec={'values':assignment,'operations':[o['id'] for o in selected],'concession_cost':cost}
            key=digest(assignment)
            if key not in found or cost<found[key]['concession_cost']:found[key]=rec
    return sorted(found.values(),key=lambda x:(x['concession_cost'],digest(x['values'])))
