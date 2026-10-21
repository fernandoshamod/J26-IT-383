"""Reviewed HTTP Twin -> Scene V1. No stock or authority inferred from detections.

HTTP objects have fixed-only semantics. Additional stock/movement admissions are
unsupported until independently reviewed contracts exist. External Scene/EAG
execution is refused by the unchanged downstream engines, even for a valid Twin.
"""
import copy,json,sqlite3,hashlib,math
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
VERSION='REVIEWED_HTTP_TWIN_TO_SCENE_V1'
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def filehash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
 p=Path(p).resolve();assert p.is_relative_to(H);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
class AdmissionError(ValueError):pass
def current(receipt,db):
 """Read immutable registered body and re-run the unchanged review/evidence gate."""
 from contracts import TwinReview
 from review_gate import reviewed_metric_twin
 p=Path(db).resolve()
 if not p.is_relative_to(H) or not p.is_file():raise AdmissionError('REGISTERED_DATABASE_REQUIRED')
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  latest=db.execute('SELECT MAX(version) FROM twins WHERE venue_id=?',(receipt['venue_id'],)).fetchone()[0]
  row=db.execute('SELECT sha,body FROM twins WHERE venue_id=? AND version=?',(receipt['venue_id'],receipt['venue_version'])).fetchone()
 if row is None:raise AdmissionError('REVIEWED_TWIN_NOT_REGISTERED')
 if latest!=receipt['venue_version']:raise AdmissionError('STALE_VENUE_VERSION')
 t=json.loads(row[1])
 if row[0]!=receipt['twin_sha256'] or digest(t)!=row[0]:raise AdmissionError('STORED_TWIN_HASH_MISMATCH')
 if t!=receipt['metric_twin']:raise AdmissionError('RECEIPT_REGISTERED_BODY_MISMATCH')
 rebuilt=reviewed_metric_twin(TwinReview.model_validate(t['review_record']),t['candidate_bundle'])
 if rebuilt!=t:raise AdmissionError('TWIN_REVIEW_REPLAY_MISMATCH')
 return t
def convert(receipt,db,brief,out):
 """An explicit event brief is mandatory and never inferred from the image."""
 import runtime
 from models import Request
 from models import venue_payload
 from shapely.geometry import Polygon
 t=current(receipt,db);record=t['review_record'];src=t['source'];old=copy.deepcopy(brief)
 if src['domain']!='controlled_synthetic':raise AdmissionError('EXTERNAL_SCENE_EAG_EXECUTION_UNSUPPORTED_GENUINE_SCENE_AUTHORITY_REQUIRED')
 if old['venue']['source']['sha256']!=src['sha256']:raise AdmissionError('EVENT_BRIEF_SOURCE_MISMATCH')
 if old['venue']['review']['scope']!='SIMULATED_FIXTURE' or any(old[p]['scope']!='SIMULATED_FIXTURE' for p in ['client','planner']):raise AdmissionError('CONTROLLED_SCOPE_MISMATCH')
 # Validate the supplied role approvals and inventory actions before transformation.
 original=Request.model_validate(old)
 for party,payload in [(original.client,runtime.common.read(original.client.evidence.path)),(original.planner,runtime.common.read(original.planner.evidence.path))]:
  if party.approval_status!='approved':raise AdmissionError('EVENT_PARTY_APPROVAL_REQUIRED')
 from models import party_payload,planner_payload
 runtime.common.assert_evidence(original.client.evidence,src['sha256'],party_payload(original.client))
 runtime.common.assert_evidence(original.planner.evidence,src['sha256'],planner_payload(original))
 source=dict(path=src['path'],sha256=src['sha256'],width_px=src['width_pixels'],height_px=src['height_pixels'],domain=src['domain'],origin='CONTROLLED_GENERATOR')
 existing=[];raw_by={o['object_id']:o for o in record['objects']}
 for ob in t['fixed_objects']:
  ro=raw_by[ob['object_id']]
  if ro['status']!='fixed':raise AdmissionError('HTTP_NONFIXED_STOCK_UNSUPPORTED')
  existing.append(dict(instance_id=ob['object_id'],class_name=ob['class'],footprint_m=ob['footprint_coordinates_m'],status='fixed',review_status='approved',protected=True,candidate_ref='HTTP_REVIEW:'+digest({'candidate_refs':ob['candidate_refs'],'decision_evidence_ref':ob['decision_evidence_ref']})))
 if len(existing)!=len(raw_by):raise AdmissionError('OBJECT_IDENTITY_MAPPING_NOT_BIJECTIVE')
 # No omitted/extra observed stock; event supply is separately derived by compiler.
 supplied={o['instance_id']:o for o in old['venue']['existing']}
 if set(supplied)!={o['instance_id'] for o in existing}:raise AdmissionError('UNREGISTERED_STOCK_OR_MISSING_OBJECT')
 for ob in existing:
  previous=supplied[ob['instance_id']]
  a,b=Polygon(previous['footprint_m']),Polygon(ob['footprint_m'])
  if previous['class_name']!=ob['class_name'] or previous['status']!='fixed' or not previous['protected'] or a.hausdorff_distance(b)>1e-8 or a.symmetric_difference(b).area>1e-8:raise AdmissionError('BRIEF_STOCK_CONFLICT')
 controls=[dict(a_px=c['point_a_px'],b_px=c['point_b_px'],distance_m=c['known_distance_m']) for c in t['calibration']['controls']]
 venue=dict(venue_id=t['venue_id'],version=t['venue_version'],source=source,boundary_px=record['boundary_px'],origin_px=t['calibration']['metric_origin_px'],controls=controls,boundary_m=t['boundary_polygon_m'],existing=existing,review=dict(status='approved',reviewer_id=t['review']['reviewer_id'],scope='SIMULATED_FIXTURE',evidence=runtime.fixtures.stub()))
 old['venue']=venue
 # Explicit test-only evidence attests the deterministic conversion, not a human.
 old=runtime.fixtures.seal(old,Path(out)/'DERIVED_CONTROLLED_RECORDS')
 req=Request.model_validate(old);checks=runtime.oracle.validate_spec(old,runtime.compiler.compile_scene(old,runtime.POLICY),runtime.POLICY)
 if not checks['valid']:raise AdmissionError('INDEPENDENT_SCENE_SPEC_INVALID:'+str(checks))
 binding=dict(schema=VERSION,receipt_sha256=digest(receipt),registered_db=str(Path(db).resolve()),venue_id=t['venue_id'],venue_version=t['venue_version'],twin_sha256=receipt['twin_sha256'],source_sha256=src['sha256'],review_record_sha256=t['review_record_sha256'],candidate_bundle_sha256=t['candidate_bundle_sha256'],source=src,calibration=t['calibration'],review_record=record,model_prediction_provenance=t['candidate_bundle'],metric_twin=t,scene_venue_payload_sha256=digest(venue_payload(req.venue)),original_event_brief_sha256=digest(brief),client=brief['client'],planner=brief['planner'],stock_actions=brief['actions'],objects=existing,flags=dict(metric_reviewed=True,physical_truth_authenticated=False,detailed_safety_validated=False,topology_connectivity_certified=False,uncertain_stock_admitted=False,movable_stock_admitted=False,experimental_symbols_counted_as_stock=False),authority_scope='SIMULATED_FIXTURE_NOT_GENUINE_CONSENT',independent_spec_check=checks)
 write(Path(out)/'MAPPING.json',binding);write(Path(out)/'SCENE_REQUEST.json',old)
 return old,binding
def verify_scene(packet,binding):
 """Admission freshness and fixed geometry are rechecked before/after EAG calls."""
 from models import Request,venue_payload
 receipt=read(H/'HTTP/TWIN_RECEIPT.json');current(receipt,binding['registered_db'])
 state=read(binding['authority_state_path'])
 if state!=dict(status='active',twin_sha256=binding['twin_sha256'],scope='SIMULATED_FIXTURE'):raise AdmissionError('ADAPTER_AUTHORITY_REVOKED_OR_MISMATCH')
 v=Request.model_validate(packet['scene']).venue
 payload=venue_payload(v)
 # A pending-review negative case is allowed to reach the original refusal gate.
 payload['review']['status']='approved'
 if digest(payload)!=binding['scene_venue_payload_sha256']:raise AdmissionError('SCENE_VENUE_CHANGED_WITHOUT_NEW_HTTP_REVIEW')
 return dict(valid=True,twin_sha256=binding['twin_sha256'],source_sha256=binding['source_sha256'],authority_status='active',metric_and_fixed_geometry_unchanged=True)
def install(runtime,out):
 """Connect original worker's fixture inlet and guard its original EAG runner."""
 import scenarios,repair
 runtime.common.HERE=Path(out);runtime.bridge.HERE=Path(out)
 receipt=read(H/'HTTP/TWIN_RECEIPT.json');brief=read(H/'SCENE_BRIEF.json')
 scene,binding=convert(receipt,H/'HTTP/research.sqlite3',brief,Path(out)/'HTTP_ADAPTER')
 binding['authority_state_path']=str(Path(out)/'ADAPTER_AUTHORITY_STATE.json')
 write(Path(out)/'ADAPTER_AUTHORITY_STATE.json',dict(status='active',twin_sha256=receipt['twin_sha256'],scope='SIMULATED_FIXTURE'))
 write(Path(out)/'HTTP_ADAPTER/LIVE_BINDING.json',binding)
 def initial(folder,width,height):
  if width!=32 or height!=24:raise AdmissionError('FIXTURE_DIMENSION_MISMATCH')
  c=dict(version=1,scope='SIMULATED_FIXTURE',scenario='CONTROLLED_NOMINAL',protected_object_ids=[o['instance_id'] for o in scene['venue']['existing']],allowed_groups=[],new_supply_permitted=True,requested_group=None,object_moves=[],reference_sha256=None)
  return runtime.seal_packet(scene,c,folder)
 original=repair.run
 original_facts=repair.facts
 def checked_facts(packet):
  verify_scene(packet,binding)
  return original_facts(packet)
 repair.facts=checked_facts
 def guarded(packet,folder,method,seed,reference=None):
  before=verify_scene(packet,binding)
  result,graph=original(packet,folder,method,seed,reference)
  after=verify_scene(packet,binding)
  write(Path(folder)/'ADAPTER_ADMISSION_REPLAY.json',dict(before=before,after=after,original_result_sha256=digest(result)))
  return result,graph
 scenarios.initial=initial;repair.run=guarded
