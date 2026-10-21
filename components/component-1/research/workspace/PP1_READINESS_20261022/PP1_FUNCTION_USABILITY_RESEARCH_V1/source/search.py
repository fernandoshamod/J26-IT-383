"""Actual pymoo NSGA-II over unchanged joint decoder/objectives. No new algorithm claim."""
from usability_env import *
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.repair import Repair
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

class AccessRepair(Repair):
    def __init__(self,c,method):super().__init__();self.c=c;self.method=method;self.trace=[];self.access_queries=0;self.trials=0
    def _do(self,problem,X,random_state=None,**kwargs):
        rng=random_state;out=X.copy();c=self.c
        for n,row in enumerate(X):
            x=jc.canonical(row,c);fails,_=access_fitness(x,c);self.access_queries+=1
            # NEW's function-labelled witness reduces exactly to B2's disconnected variable block.
            if self.method=='NEW':eligible=[f['block'] for f in fails if not(f['block']==0 and 'locked_group_0' in c)]
            else:eligible=[a['block'] for a in fails if a['block']!=0 or 'locked_group_0' not in c]
            moved=None
            if eligible:
                b=eligible[int(rng.integers(len(eligible)))];idx=jc.BLOCKS[b]
                _,units,*_=jc.geometry(x,c)
                for attempt in range(16):
                    self.trials+=1;candidate=x.copy();candidate[idx[:2]]=rng.uniform([2.5,2.5],[29.5,21.5])
                    _,nu,*_=jc.geometry(candidate,c);q=nu[b]
                    if q is None:break
                    if not Polygon(c['boundary']).covers(q):continue
                    if any(q.distance(Polygon(o['polygon']))<c['clearance_m'] for o in c['fixed']):continue
                    if any(q.distance(p)<c['clearance_m'] for j,p in enumerate(units) if j!=b and p is not None):continue
                    # Full connectivity witness, identical oracle and limits for NEW and B2.
                    nf,_=access_fitness(candidate,c);self.access_queries+=1
                    if not any(a['block']==b for a in nf):x=candidate;moved=b;break
            out[n]=x
            self.trace.append({'input':jc.canonical(row,c).tolist(),'output':x.tolist(),'failed_blocks':[f['block'] for f in fails],'moved_block':moved})
        return out

def solve(c,method,seed,reference=None,budget=240):
    start=time.perf_counter();jc.admit(c,reference)
    local=jc.Measures(c,reference);trace=[]
    lo=np.array([0.,0.]*4+[0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,4.])
    hi=np.array([32.,24.]*4+[32.,24.,1.,32.,24.,1.,32.,24.,1.,2.,32.,24.,7.])
    class Problem(ElementwiseProblem):
        def __init__(self):super().__init__(n_var=21,n_obj=3,n_ieq_constr=1,xl=lo,xu=hi)
        def _evaluate(self,x,out,*args,**kwargs):
            f,g=local.measure(x);fails,_=access_fitness(x,c)
            v=g[0]+(len(fails) if method!='B0' else 0.)
            out['F']=f;out['G']=[v]
            trace.append({'x':jc.canonical(x,c).tolist(),'F':f,'local_cv':g[0],'access_failures':fails,'cv':v})
    rng=np.random.default_rng(seed);base=np.array(reference['decision_vector'] if reference else c['seed_design'])
    if c['minimum_buffets']==2:base[17]=2
    samples=rng.uniform(lo,hi,(40,21));samples[0]=base
    for i in range(1,32):samples[i]=np.clip(base+rng.normal(0,.18,21),lo,hi)
    repair=AccessRepair(c,method) if method in ['B2','NEW'] else None
    opts=dict(pop_size=40,sampling=samples,eliminate_duplicates=False)
    if repair:opts['repair']=repair
    opt=minimize(Problem(),NSGA2(**opts),('n_eval',budget),seed=seed,verbose=False,copy_algorithm=False)
    seen={}
    for x in ([] if opt.X is None else np.atleast_2d(opt.X)):
        v=jc.canonical(x,c);seen.setdefault(tuple(np.round(v,8)),v)
    # Fixed bounded reporting policy, not three fabricated alternatives.
    layouts=[jc.export_layout(v,c,reference) for v in list(seen.values())[:4]]
    return dict(method=method,seed=seed,status='RETURNED' if layouts else 'NO_FEASIBLE_RETURNED_WITHIN_BUDGET',evaluations=int(opt.algorithm.evaluator.n_eval),runtime_s=time.perf_counter()-start,candidates=layouts,trace=trace,repair_trace=repair.trace if repair else [],repair_access_queries=repair.access_queries if repair else 0,repair_pose_trials=repair.trials if repair else 0,fitness_access_queries=len(trace),case_sha256=digest(c),reference_sha256=digest(reference) if reference else None)
