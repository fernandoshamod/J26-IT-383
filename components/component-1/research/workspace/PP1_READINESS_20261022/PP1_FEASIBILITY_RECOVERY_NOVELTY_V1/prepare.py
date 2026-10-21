from io_context import *
from experiment import make_requests,SEEDS,BUDGET
if __name__=='__main__':
    snap=snapshot();assert not snap['pin_mismatches'],snap['pin_mismatches'];save(H/'PRESERVATION_BEFORE.json',snap)
    save(H/'FROZEN_PROTOCOL.json',{'scope':'CONTROLLED_WEDDING_SINGLE_EVENT_ONLY','venues':['venue_1','venue_2'],'seeds':SEEDS,'budget_per_state':BUDGET,'scenario_count':9,'requests':[{'venue':v,'seed':s,'request':r,'sha256':digest(r)} for v in ['venue_1','venue_2'] for s in SEEDS for r in make_requests(v,s)],'hypothesis':'Dependency/authority-aware grouped recovery is correct and conventionally expressible; no new algorithm presumed','search_oracle_shared':True,'simulated_concession_costs':True,'failed_search_is_not_unsat':True})
    print('PREPARED',len(snap['files']),'preserved dependency/evidence hashes; 36 frozen controlled queries')
