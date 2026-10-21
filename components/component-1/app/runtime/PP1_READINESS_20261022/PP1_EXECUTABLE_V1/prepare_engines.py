"""Create isolated, reviewable adaptations of frozen F2B/F2D; no original edits.
Search operators, RNG, populations, generations, radii and reconstruction are reused.
"""
import ast,difflib,textwrap
from support import ROOT,PACKAGE,save,filehash
def write(name,original,updated):
    with (PACKAGE/name).open('x',encoding='utf-8') as f:f.write(updated)
    with (PACKAGE/(name+'.diff')).open('x',encoding='utf-8') as f:f.writelines(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='frozen/'+name,tofile='isolated/'+name))
def main():
    base=ROOT/'PP1_STAGE_E_RESEARCH_CORE/research';initial=(base/'f2b_live_research_engine_v2.py').read_text();source=initial[:initial.index("if __name__")]
    a=source.index('def validate(req):');b=source.index('def initialize(',a);source=source[:a]+'from engine_support import validate_metric as validate, select_nondominated, limits\n\n'+source[b:]
    source=source.replace('        return {\n            "F": [stage_distance, displacement],','        constraints.extend(limits(req, stage_distance, displacement))\n        return {\n            "F": [stage_distance, displacement],')
    source=source.replace('    n_constraints = count + count * len(fixed) + count * (count - 1) // 2','    n_constraints = count + count * len(fixed) + count * (count - 1) // 2 + len(limits(req,0.0,0.0))')
    source=source.replace('    assert measure(reference.flatten())["feasible"]','    # Geometry initializer remains original; additional hard upper bounds may\n    # require search before a feasible result is found. No failed reference is exported.')
    source=source.replace('    best = min(solutions, key=lambda x: measure(x)["F"][0])\n    m = measure(best)','    candidates = []\n    for alternative_index, best in enumerate(select_nondominated(solutions, measure)):\n        m = measure(best)')
    start=source.index('    # Reconstruct all individual physical footprints.');end=source.index('    return {\n        "contract_id":',start)
    render=source[start:end].replace('len(objects) == 3 + count * 9','len(objects) == len(records) + count * 9')
    tree=ast.parse(textwrap.dedent(source[end:]));ret=tree.body[0].value;candidate=next(v for k,v in zip(ret.keys,ret.values) if k.value=='candidate_layouts').elts[0];candidate_text=ast.unparse(candidate).replace("'live_best_stage_proximity'","f'pareto_{alternative_index:03d}'")
    source=source[:start]+''.join('    '+line if line.strip() else line for line in render.splitlines(True))+'        candidates.append('+candidate_text+')\n\n'+source[end:]
    old='"candidate_layouts": [{';i=source.index(old);j=source.index('        "permission_decisions":',i);source=source[:i]+'"candidate_layouts": candidates,\n'+source[j:]
    write('engine_initial.py',initial,source)
    adaptive=(base/'f2d_live_adaptive_engine_v1.py').read_text();s=adaptive[:adaptive.index("if __name__")];s=s.replace('from f2b_live_research_engine_v1 import validate as validate_initial','from engine_support import validate_metric as validate_initial, select_nondominated, limits')
    s=s.replace('    if count != 20:\n        raise ValueError("V1_ADAPTIVE_REQUIRES_20_GROUPS")\n','')
    s=s.replace('len(groups) != 20','len(groups) != count').replace('range(1, 21)','range(1, count + 1)').replace('len(original_items) != 183','len(original_items) != len(fixed) + count * 9').replace('len(items) != 183','len(items) != len(fixed) + count * 9')
    # Preserve the original synthetic move-permission gate unchanged.
    # Real-source adaptive scope remains explicitly unsupported by the service.
    s=s.replace('        return {\n            "F": [','        all_mean = (sum(math.dist(v,stage_xy) for k,v in original.items() if k != move_id) + float(np.linalg.norm(xy-stage_xy))) / count\n        constraints.extend(limits(req,all_mean,float(np.linalg.norm(xy-start))))\n        return {\n            "F": [')
    s=s.replace('n_ieq_constr=len(protected) + 1,','n_ieq_constr=len(protected) + 1 + len(limits(req,0.0,0.0)),')
    # Start must satisfy original geometric reference checks; added objective
    # bounds may need search. Final exported solutions must satisfy all limits.
    s=s.replace('    if not measure(start)["feasible"]:\n        raise ValueError("REFERENCE_PERMISSION_GEOMETRY_INVALID")','    if any(g > 1e-7 for g in measure(start)["G"][:len(protected)+1]):\n        raise ValueError("REFERENCE_PERMISSION_GEOMETRY_INVALID")')
    i=s.index('    choices = [');j=s.index('    candidates = []',i)
    s=s[:i]+"    selected = select_nondominated([xy for xy,m in feasible], measure)\n    choices = [(f'pareto_{i:03d}', (xy, measure(xy))) for i,xy in enumerate(selected)]\n"+s[j:]
    write('engine_adaptive.py',adaptive,s)
    save(PACKAGE/'ENGINE_LINEAGE.json',{'initial_source':str(base/'f2b_live_research_engine_v2.py'),'initial_source_sha256':filehash(base/'f2b_live_research_engine_v2.py'),'adaptive_source':str(base/'f2d_live_adaptive_engine_v1.py'),'adaptive_source_sha256':filehash(base/'f2d_live_adaptive_engine_v1.py'),'changes':['Explicit metric geometry validation replaces fixed fixture equality restriction','Retain original NSGA-II operators/populations/generations and individual reconstruction','Expose only feasible unique nondominated alternatives','Enforce declared stage/movement upper bounds','Adaptive group count is request-derived, still only one group per move'],'unchanged_originals':True})
if __name__=='__main__':main()
