import copy,math,uuid,threading,importlib.util,sys
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
from support import PACKAGE,ROOT,digest,filehash,ResearchError,read
from contracts import Optimize
from requirements import reconcile
from storage import Store
from verification import verify_final
sys.path.insert(0,str(ROOT/'PP1_STAGE_E_RESEARCH_CORE/research'))
class Service:
    def __init__(self,db):
        self.store=Store(db);self.lock=threading.Lock();self.minimize_calls=0;self.last_evaluations=0
    def engine(self,name):
        path=PACKAGE/(name+'.py');spec=importlib.util.spec_from_file_location('isolated_'+uuid.uuid4().hex,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        real=m.minimize
        def observed(*a,**k):
            self.minimize_calls+=1;result=real(*a,**k);self.last_evaluations=int(result.algorithm.evaluator.n_eval);return result
        m.minimize=observed;return m
    def reject(self,request,error,evaluations=0):
        response=dict(contract_id='COMPONENT1_PP1_EXECUTABLE_V1',run_id=uuid.uuid4().hex,status=error.status,reason=error.code,details=error.details,candidate_layouts=[],optimizer_evaluations=evaluations,scope='local_research',real_planner_authentication=False)
        response['xai']=dict(response_id=response['run_id'],request_sha256=digest(request),response_payload_sha256=digest(response),decision=error.status,reasons=[error.code],evidence=error.details,optimizer_evaluations=evaluations,no_counterfactual_performance_claim=True)
        return self.store.save_run(request,response)
    def optimize(self,request:Optimize):
        raw=request.model_dump()
        with self.lock:
            self.last_evaluations=0
            try:return self._optimize(request,raw)
            except ResearchError as e:return self.reject(raw,e,self.last_evaluations)
            except ValueError as e:
                text=str(e);status='infeasible' if any(k in text for k in ['NO_COMPLETE_INITIALIZATION','NO_FEASIBLE_CANDIDATES']) else 'error'
                return self.reject(raw,ResearchError(text,{'global_infeasibility_proven':False},status),self.last_evaluations)
    def _optimize(self,req,raw):
        twin=self.store.twin(req.venue_id,req.venue_version,req.twin_sha256);resolved=reconcile(req.requirements)
        from evidence import verify_evidence_artifacts
        verify_evidence_artifacts(twin['review_record'])
        from PIL import Image
        source=Path(twin['source']['path'])
        if not source.is_file() or filehash(source)!=twin['source']['sha256']:raise ResearchError('REGISTERED_SOURCE_CHANGED')
        scope='SIMULATED_FIXTURE_REVIEW' if twin['source']['domain']=='controlled_synthetic' else 'EXTERNAL_RESEARCH_REVIEW'
        fixed=[{k:o[k] for k in ['object_id','class','group_id','footprint_coordinates_m']} for o in twin['fixed_objects']]
        internal=dict(contract_id='STAGE_E_PP1_V1',mode='initial_design',venue_twin={'source_type':twin['source']['domain'],'verification_status':'explicit_review_input','boundary_polygon_m':twin['boundary_polygon_m'],'fixed_obstacles':fixed},event_requirements={'event_id':req.requirements.event_id,'event_type':'Wedding','guest_count':req.requirements.guest_count,'seats_per_table':8},optimization_request={'algorithm':'NSGA2','experimental_clearance_m':resolved['minimum_clearance_m'],'seed':req.seed},hard_limits={k:resolved[k] for k in ['maximum_mean_stage_distance_m','maximum_total_movement_m']})
        reference_layout=None;reference=None;locked=set();group_changes={'removed':[],'added':[]};prior_req=None
        if req.mode=='initial_design':
            if req.reference or req.affected_group_ids or req.remove_group_ids or req.permissions:raise ResearchError('INITIAL_DESIGN_CANNOT_CARRY_REVISION_DATA')
            if resolved['protected_group_ids'] or set(resolved['protected_object_ids'])-set(o['object_id'] for o in fixed):raise ResearchError('INITIAL_DESIGN_HAS_NO_EXISTING_GROUP_IDENTITIES')
            engine=self.engine('engine_initial');initialize=engine.initialize;captured={}
            def capture(*a,**k):
                x=initialize(*a,**k);captured['centers']={f'seating_group_{i+1:04d}':xy.tolist() for i,xy in enumerate(x)};return x
            engine.initialize=capture;result=engine.run(internal);reference=captured['centers']
        else:
            if req.reference is None:raise ResearchError('APPROVED_REFERENCE_REQUIRED')
            reference_layout,prior_req=self.store.reference(req.reference,req);reference=reference_layout['group_centers_m']
            if prior_req['requirements']['event_id']!=req.requirements.event_id:raise ResearchError('REFERENCE_EVENT_MISMATCH')
            allobjects={o['object_id']:o for o in reference_layout['objects']}
            protected=set(resolved['protected_group_ids'])|set(prior_req['requirements'].get('protected_group_ids',[]))
            for oid in set(resolved['protected_object_ids'])|set(prior_req['requirements'].get('protected_object_ids',[])):
                if oid not in allobjects:raise ResearchError('UNKNOWN_PROTECTED_OBJECT_ID',{'object_id':oid})
                if allobjects[oid].get('group_id'):protected.add(allobjects[oid]['group_id'])
            if not protected.issubset(set(reference)):raise ResearchError('UNKNOWN_PROTECTED_GROUP_ID')
            if len({(p.group_id,p.action) for p in req.permissions})!=len(req.permissions):raise ResearchError('DUPLICATE_PERMISSION')
            permissions={(p.group_id,p.action):p for p in req.permissions}
            def permitted(g,action):
                p=permissions.get((g,action))
                if g in protected:raise ResearchError('PROTECTED_ID_CHANGE_DENIED',{'group_id':g},'denied')
                if p is None or not p.approved or p.scope!=scope:raise ResearchError('EXPLICIT_ACTION_PERMISSION_REQUIRED',{'group_id':g,'action':action},'denied')
                return p
            if req.mode=='adaptive_revision':
                if twin['source']['domain']!='controlled_synthetic':raise ResearchError('REAL_ADAPTIVE_PERMISSION_SCOPE_NOT_VALIDATED')
                if len(req.affected_group_ids)!=1 or req.remove_group_ids:raise ResearchError('LIVE_ADAPTIVE_REQUIRES_ONE_AFFECTED_GROUP')
                if len(reference)*8!=req.requirements.guest_count:raise ResearchError('USE_GUEST_CHANGE_MODE_FOR_CAPACITY_CHANGE')
                target=req.affected_group_ids[0]
                if target not in reference:raise ResearchError('UNKNOWN_AFFECTED_GROUP')
                permission=permitted(target,'move');locked=set(reference)-{target}
                internal.update(mode='adaptive_revision',approved_reference_layout={'group_centers_m':reference,'approval_status':'SIMULATED_RESEARCH_REFERENCE'},revision_request={'group_id':target,'action':'move'},planner_context={'permissions':{target:dict(status='movable',move_allowed=True,scope='SYNTHETIC_DEMO_ONLY',approved_by=permission.reviewer_id,approval_reason=permission.reason)}})
                # Validate the full approved reference before entering the optimizer.
                checkreq=copy.deepcopy(internal);checkreq['mode']='initial_design';checklayout=copy.deepcopy(reference_layout);checklayout['objective_metrics']={'average_stage_distance_m':self.mean_stage(reference,fixed),'reference_displacement_m':0.0}
                verify_final(checklayout,checkreq,reference,reference_layout,{**resolved,'maximum_mean_stage_distance_m':None,'maximum_total_movement_m':None},set(reference))
                engine=self.engine('engine_adaptive');result=engine.execute(internal)
                if result['status']!='success':raise ResearchError('INTERNAL_PERMISSION_DENIAL',result.get('permission_decisions'),status='denied')
            else:
                if req.affected_group_ids:raise ResearchError('GUEST_REDUCTION_DOES_NOT_MOVE_RETAINED_GROUPS')
                oldcount=len(reference);newcount=resolved['groups']
                if newcount>=oldcount:raise ResearchError('LIVE_GUEST_ADDITION_NOT_IMPLEMENTED',{'current_groups':oldcount,'requested_groups':newcount})
                removed=req.remove_group_ids
                if len(removed)!=len(set(removed)) or len(removed)!=oldcount-newcount or not set(removed).issubset(reference):raise ResearchError('GUEST_REMOVAL_ID_COUNT_CONFLICT')
                for g in removed:permitted(g,'remove')
                group_changes['removed']=removed;reference={g:xy for g,xy in reference.items() if g not in removed};locked=set(reference);internal['expected_group_ids']=sorted(reference)
                objects=[copy.deepcopy(o) for o in reference_layout['objects'] if o.get('group_id') not in removed]
                layout=dict(layout_id='preserved_after_approved_guest_reduction',objects=objects,group_centers_m=reference,objective_metrics={'average_stage_distance_m':self.mean_stage(reference,fixed),'reference_displacement_m':0.0})
                result={'candidate_layouts':[layout],'provenance':{'optimizer_evaluations':0,'algorithm_version':'APPROVED_REMOVAL_PRESERVE_RETAINED_GEOMETRY'}}
        # Enforce finiteness, full physical replay, count/class/identity/locks and
        # every declared hard limit independently before any successful write.
        candidates=[];verified={};seen=set()
        for layout in result['candidate_layouts']:
            if req.mode=='initial_design':key=tuple(sorted(tuple(round(v,8) for v in xy) for xy in layout['group_centers_m'].values()))
            else:key=digest(layout['group_centers_m'])
            if key in seen:continue
            seen.add(key);metrics=verify_final(layout,internal,reference,reference_layout,resolved,locked)
            layout['constraint_results']={'independently_verified':True,'outside_count':metrics['outside_count'],'overlap_count':metrics['overlap_count'],'locked_object_changes':metrics['locked_object_vertex_changes'],'minimum_clearance_m':metrics['minimum_clearance']};metrics['layout_sha256']=digest(layout);verified[layout['layout_id']]=metrics;candidates.append(layout)
        if not candidates:raise ResearchError('NO_VERIFIED_DISTINCT_ALTERNATIVES',status='infeasible')
        preference=resolved['alternative_preference'];vectors=[]
        for l in candidates:
            m=verified[l['layout_id']];vectors.append([m['mean_stage_distance'],m['total_group_movement'] if req.mode!='initial_design' else m['assignment_movement']])
        values=np.array(vectors);normalized=(values-values.min(0))/np.maximum(values.max(0)-values.min(0),1e-12)
        index=int(values[:,0].argmin()) if preference=='stage_proximity' else int(values[:,1].argmin()) if preference=='minimum_disruption' else int(np.linalg.norm(normalized,axis=1).argmin())
        response=dict(contract_id='COMPONENT1_PP1_EXECUTABLE_V1',run_id=uuid.uuid4().hex,status='success',source_domain=twin['source']['domain'],venue_id=req.venue_id,venue_version=req.venue_version,twin_sha256=req.twin_sha256,actual_boundary_polygon_m=twin['boundary_polygon_m'],actual_fixed_geometry_sha256=digest(fixed),source_image_sha256=twin['source']['sha256'],candidate_layouts=candidates,selected_layout_id=candidates[index]['layout_id'],resolved_requirements=resolved,group_changes=group_changes,initialization_or_retained_reference_m=reference,verification=verified,optimizer_evaluations=self.last_evaluations,provenance={'engine':result['provenance']['algorithm_version'],'engine_lineage':read(PACKAGE/'ENGINE_LINEAGE.json'),'request_sha256':digest(raw),'review_origin':twin['approval_origin'],'review_scope':twin['review']['scope'],'alternative_preference_role':'selection_only_no_learned_preference_model','optimizer_geometry_substituted':False},real_planner_authentication=False,independent_real_venue_validation=False,safety_certified=False)
        response['xai']=make_xai(response,raw,reference,locked)
        verify_xai_binding(response,raw)
        return self.store.save_run(raw,response)
    @staticmethod
    def mean_stage(centers,fixed):
        p=Polygon(next(o['footprint_coordinates_m'] for o in fixed if o['class']=='stage'));return sum(math.dist(xy,[p.centroid.x,p.centroid.y]) for xy in centers.values())/len(centers)
def make_xai(response,request,reference,locked):
    records=[]
    for l in response['candidate_layouts']:
        m=response['verification'][l['layout_id']];moved=sorted(g for g,xy in l['group_centers_m'].items() if math.dist(xy,reference[g])>1e-9)
        records.append(dict(layout_id=l['layout_id'],layout_sha256=digest(l),affected_groups=moved,locked_groups=sorted(locked),removed_groups=response['group_changes']['removed'],object_count=m['object_count'],mean_stage_distance_m=m['mean_stage_distance'],stable_identity_group_movement_m=m['total_group_movement'],assignment_movement_m=m['assignment_movement'],individual_object_movement_m=m['total_individual_object_movement'],constraints={'outside_count':m['outside_count'],'overlap_count':m['overlap_count'],'locked_object_changes':m['locked_object_vertex_changes'],'minimum_clearance_m':m['minimum_clearance']},text=f"{m['object_count']} objects passed independent geometry checks. {len(moved)} groups moved, {len(locked)} remained locked, and {len(response['group_changes']['removed'])} groups were explicitly removed. Mean stage distance: {m['mean_stage_distance']:.6f} m. Stable-ID relocation: {m['total_group_movement']:.6f} m."))
    comparisons=[dict(baseline=a['layout_id'],compared=b['layout_id'],mean_stage_distance_delta_m=b['mean_stage_distance_m']-a['mean_stage_distance_m'],stable_movement_delta_m=b['stable_identity_group_movement_m']-a['stable_identity_group_movement_m']) for a,b in zip(records,records[1:])]
    return dict(response_id=response['run_id'],request_sha256=digest(request),response_payload_sha256=digest(response),explanations=records,alternative_comparisons=comparisons,selected_layout_id=response['selected_layout_id'],selection_preference=response['resolved_requirements']['alternative_preference'],counterfactual_performance_claim=False,learned_sgcn_used=False,weather_model_used=False,approval_scope=response['provenance']['review_scope'])
def verify_xai_binding(response,request):
    x=response.get('xai',{});base={k:v for k,v in response.items() if k!='xai'}
    if x.get('response_id')!=response.get('run_id') or x.get('request_sha256')!=digest(request) or x.get('response_payload_sha256')!=digest(base):raise ResearchError('XAI_RESPONSE_OR_REQUEST_BINDING_MISMATCH')
    if response['status']=='success':
        records={e['layout_id']:e for e in x['explanations']}
        if set(records)!={l['layout_id'] for l in response['candidate_layouts']}:raise ResearchError('XAI_LAYOUT_SET_MISMATCH')
        for l in response['candidate_layouts']:
            if records[l['layout_id']]['layout_sha256']!=digest(l):raise ResearchError('XAI_LAYOUT_HASH_MISMATCH')
        locks=set(next(iter(base['verification'].values()))['locked_group_ids'])
        expected=make_xai(base,request,base['initialization_or_retained_reference_m'],locks)
        if digest(expected)!=digest(x):raise ResearchError('XAI_NUMERIC_OR_TEXT_EVIDENCE_MISMATCH')
    elif x.get('reasons')!=[response['reason']] or x.get('optimizer_evaluations')!=response['optimizer_evaluations']:
        raise ResearchError('XAI_DENIAL_REASON_MISMATCH')
    return True
