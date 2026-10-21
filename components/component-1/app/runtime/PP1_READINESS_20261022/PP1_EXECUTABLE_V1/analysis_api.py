"""Durable image intake/inference API without a frontend or a fabricated review."""
import io,uuid,threading
from pathlib import Path
from fastapi import APIRouter,Body
from fastapi.responses import FileResponse
from PIL import Image,UnidentifiedImageError
from contracts import Strict
from support import PACKAGE,ROOT,read,save,filehash,ResearchError
from responses import ImageReceipt,AnalysisReceipt
open_png_jpeg=Image.open  # retain Pillow reader before third-party monkey patches

class Analyze(Strict):
    image_path:str

def router():
    api=APIRouter();lock=threading.Lock()
    @api.post('/images',response_model=ImageReceipt)
    def upload(body:bytes=Body(media_type='application/octet-stream')):
        if not body or len(body)>20*1024*1024:raise ResearchError('IMAGE_BYTES_EMPTY_OR_OVER_20_MIB')
        try:
            with open_png_jpeg(io.BytesIO(body),formats=['PNG','JPEG']) as im:
                fmt=im.format;w,h=im.size
                if fmt not in ['PNG','JPEG'] or w*h>16000000:raise ResearchError('UNSUPPORTED_IMAGE_FORMAT_OR_DIMENSIONS')
                im.verify()
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ResearchError('INVALID_IMAGE_BYTES')
        uid=uuid.uuid4().hex;path=PACKAGE/'outputs/API_UPLOADS'/uid/('source.png' if fmt=='PNG' else 'source.jpg');path.parent.mkdir(parents=True)
        path.write_bytes(body)
        return dict(image_id=uid,image_path=str(path.resolve()),sha256=filehash(path),width_pixels=w,height_pixels=h,physical_real_venue_provenance_verified=False)
    def folder(analysis_id):
        if len(analysis_id)!=32 or any(c not in '0123456789abcdef' for c in analysis_id):raise ResearchError('ANALYSIS_NOT_FOUND')
        out=PACKAGE/'outputs/API_ANALYSES'/analysis_id
        if not (out/'MANIFEST.json').is_file():raise ResearchError('ANALYSIS_NOT_FOUND')
        manifest=read(out/'MANIFEST.json')
        for name,sha in manifest.items():
            if Path(name).name!=name or not (out/name).is_file() or filehash(out/name)!=sha:raise ResearchError('SAVED_ANALYSIS_ARTIFACT_CORRUPTED')
        return out,manifest
    def result(analysis_id):
        out,manifest=folder(analysis_id)
        return dict(analysis_id=analysis_id,status='review_required',candidate_bundle=read(out/'CANDIDATE_BUNDLE.json'),pending_review_template=read(out/'REVIEW_CALIBRATION_TEMPLATE_PENDING.json'),model_report=read(out/'MODEL_OUTPUT_REPORT.json'),gate=read(out/'REVIEW_GATE_STATUS.json'),artifacts={name:{'sha256':sha,'url':f'/analyses/{analysis_id}/artifacts/{name}'} for name,sha in manifest.items()})
    @api.post('/analyses',response_model=AnalysisReceipt)
    def analyze(request:Analyze):
        p=Path(request.image_path).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file():raise ResearchError('SOURCE_OUTSIDE_WORKSPACE_OR_MISSING')
        try:
            with open_png_jpeg(p,formats=['PNG','JPEG']) as im:
                if im.format not in ['PNG','JPEG'] or im.width*im.height>16000000:raise ResearchError('UNSUPPORTED_IMAGE_FORMAT_OR_DIMENSIONS')
                im.verify()
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ResearchError('INVALID_IMAGE_BYTES')
        aid=uuid.uuid4().hex;out=PACKAGE/'outputs/API_ANALYSES'/aid
        from understanding import understand
        with lock:
            try:understand(p,out)
            except ValueError as e:raise ResearchError('IMAGE_ANALYSIS_REJECTED',{'cause':str(e)})
        save(out/'MANIFEST.json',{p.name:filehash(p) for p in out.iterdir() if p.is_file()})
        return result(aid)
    @api.get('/analyses/{analysis_id}',response_model=AnalysisReceipt)
    def get_analysis(analysis_id:str):return result(analysis_id)
    @api.get('/analyses/{analysis_id}/artifacts/{filename}')
    def artifact(analysis_id:str,filename:str):
        out,manifest=folder(analysis_id)
        if filename not in manifest:raise ResearchError('ANALYSIS_ARTIFACT_NOT_FOUND')
        return FileResponse(out/filename)
    return api
