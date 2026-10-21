"""Existing frozen optimization/review API plus versioned updated-model inference hook."""
from common import *
import io,uuid,threading,os
from typing import Literal
from PIL import Image,UnidentifiedImageError
open_png_jpeg=Image.open
from perception import backend_modules,understand
backend_modules()
from fastapi import APIRouter,Body
from fastapi.responses import FileResponse
from api import create_app as frozen_create_app
from contracts import Strict
from responses import ImageReceipt,AnalysisReceipt
from support import ResearchError,digest
from model_registry import verify_hashes
PACKAGE_ROOT=H.parents[2]
STATE_ROOT=Path(os.environ.get('PP1_RUNTIME_STATE',PACKAGE_ROOT/'runtime-state')).resolve()
RUN_STATE=Path(os.environ.get('PP1_RUN_STATE',STATE_ROOT/'runs'/'manual')).resolve()
UPLOAD_ROOT=RUN_STATE/'API_UPLOADS';ANALYSIS_ROOT=RUN_STATE/'API_ANALYSES'
class AnalyzeUpdated(Strict):
 image_path:str
 route:Literal['indoor','outdoor','hybrid']='indoor'
 experimental_chair:bool=False
def create_app(db_path):
 db_path=Path(db_path).resolve()
 if not db_path.is_relative_to(STATE_ROOT):raise ValueError('DATABASE_MUST_REMAIN_IN_PORTABLE_RUNTIME_STATE')
 api=APIRouter();lock=threading.Lock()
 def locate(aid):
  if len(aid)!=32 or any(c not in '0123456789abcdef' for c in aid):raise ResearchError('ANALYSIS_NOT_FOUND')
  out=ANALYSIS_ROOT/aid
  if not (out/'MANIFEST.json').is_file():raise ResearchError('ANALYSIS_NOT_FOUND')
  manifest=read(out/'MANIFEST.json')
  for name,h in manifest.items():
   if Path(name).name!=name or not (out/name).is_file() or sha(out/name)!=h:raise ResearchError('SAVED_ANALYSIS_ARTIFACT_CORRUPTED')
  source=read(out/'CANDIDATE_BUNDLE.json')['source']
  if not Path(source['path']).is_file() or sha(source['path'])!=source['sha256']:raise ResearchError('SAVED_ANALYSIS_SOURCE_CHANGED')
  return out,manifest
 def receipt(aid):
  out,manifest=locate(aid)
  r=dict(analysis_id=aid,status='review_required',candidate_bundle=read(out/'CANDIDATE_BUNDLE.json'),pending_review_template=read(out/'REVIEW_CALIBRATION_TEMPLATE_PENDING.json'),model_report=read(out/'MODEL_OUTPUT_REPORT.json'),gate=read(out/'REVIEW_GATE_STATUS.json'),artifacts={n:{'sha256':v,'url':f'/analyses/{aid}/artifacts/{n}'} for n,v in manifest.items()})
  return AnalysisReceipt.model_validate(r)
 @api.post('/images',response_model=ImageReceipt)
 def upload(body:bytes=Body(media_type='application/octet-stream')):
  if not body or len(body)>20*1024*1024:raise ResearchError('IMAGE_BYTES_EMPTY_OR_OVER_20_MIB')
  try:
   with open_png_jpeg(io.BytesIO(body),formats=['PNG','JPEG']) as im:
    fmt=im.format;w,h=im.size
    if w*h>16000000:raise ResearchError('UNSUPPORTED_IMAGE_FORMAT_OR_DIMENSIONS')
    im.verify()
  except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ResearchError('INVALID_IMAGE_BYTES')
  uid=uuid.uuid4().hex;p=UPLOAD_ROOT/uid/('source.png' if fmt=='PNG' else 'source.jpg');p.parent.mkdir(parents=True);p.write_bytes(body)
  return dict(image_id=uid,image_path=str(p),sha256=sha(p),width_pixels=w,height_pixels=h,physical_real_venue_provenance_verified=False)
 @api.post('/analyses',response_model=AnalysisReceipt)
 def analyze(request:AnalyzeUpdated):
  p=Path(request.image_path).resolve()
  if not p.is_relative_to(PACKAGE_ROOT) or not p.is_file():raise ResearchError('SOURCE_OUTSIDE_PORTABLE_PACKAGE_OR_MISSING')
  try:
   with open_png_jpeg(p,formats=['PNG','JPEG']) as im:
    if im.width*im.height>16000000:raise ResearchError('UNSUPPORTED_IMAGE_FORMAT_OR_DIMENSIONS')
    im.verify()
  except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ResearchError('INVALID_IMAGE_BYTES')
  aid=uuid.uuid4().hex;out=ANALYSIS_ROOT/aid
  with lock:
   try:understand(p,out,request.route,request.experimental_chair)
   except (ValueError,RuntimeError) as exc:raise ResearchError('IMAGE_ANALYSIS_REJECTED',{'cause':str(exc)})
  save(out.relative_to(H)/'MANIFEST.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
  return receipt(aid)
 @api.get('/analyses/{analysis_id}',response_model=AnalysisReceipt)
 def get_analysis(analysis_id:str):return receipt(analysis_id)
 @api.get('/analyses/{analysis_id}/artifacts/{filename}')
 def artifact(analysis_id:str,filename:str):
  out,manifest=locate(analysis_id)
  if filename not in manifest:raise ResearchError('ANALYSIS_ARTIFACT_NOT_FOUND')
  return FileResponse(out/filename)
 # Current installed FastAPI keeps included routers lazily; deleting flattened routes
 # does not replace an included router. Supply the replacement at construction time.
 import analysis_api
 old_factory=analysis_api.router
 analysis_api.router=lambda:api
 analysis_api.Analyze=AnalyzeUpdated  # frozen /contracts imports this symbol at request time
 try:app=frozen_create_app(db_path)
 finally:analysis_api.router=old_factory
 app.state.integration_models={'status':'lazy_private_weights_checked_on_inference'};app.state.updated_model_adapter=True
 app.state.integration_version='COMPONENT1_UPDATED_MODEL_INTEGRATION_V1'
 app.title='Component 1 verified backend with updated model adapter'
 app.description='Base API 1.1.0 with versioned AnalyzeUpdated optional route/experimental_chair fields. Pending review is mandatory. Scene/EAG lifecycle uses existing separate contracts through the integration CLI.'
 return app
