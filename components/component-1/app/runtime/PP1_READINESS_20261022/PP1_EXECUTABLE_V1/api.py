from typing import Any
from fastapi import FastAPI,HTTPException,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contracts import Strict,TwinReview,Optimize,Approve,Revoke
from review_gate import reviewed_metric_twin
from service import Service
from support import ResearchError
from responses import OptimizationResponse,StoredRun,TwinReceipt,ApprovalReceipt,RevocationReceipt,RunIndex,Health,GateError,NonSuccess
class Register(Strict):
    review:TwinReview
    candidate_bundle:dict[str,Any]
def create_app(db_path):
    service=Service(db_path);app=FastAPI(title='Component 1 executable research backend',version='1.1.0',responses={422:{'model':GateError|NonSuccess,'description':'Gate/domain error or persisted schema rejection. Check reason/status.'}});app.state.service=service
    from analysis_api import router
    app.include_router(router())
    @app.exception_handler(ResearchError)
    async def research_error(request,exc):return JSONResponse(status_code=422,content={'reason':exc.code,'details':exc.details})
    @app.exception_handler(RequestValidationError)
    async def invalid_schema(request,exc):
        # Keep a denial record without trying to persist non-finite/raw JSON as a successful request.
        raw=(await request.body()).decode('utf-8',errors='replace');details=[{'location':list(e['loc']),'type':e['type'],'message':e['msg']} for e in exc.errors()]
        result=service.reject({'raw_request_text':raw},ResearchError('STRICT_REQUEST_SCHEMA_REJECTED',{'errors':details}))
        return JSONResponse(status_code=422,content=result)
    @app.get('/health',response_model=Health)
    def health():return {'status':'ready','scope':'local_research','real_authentication':False,'database':str(service.store.path)}
    @app.post('/twins',response_model=TwinReceipt)
    def register(request:Register):
        twin=reviewed_metric_twin(request.review,request.candidate_bundle);h=service.store.register(twin)
        return {'venue_id':twin['venue_id'],'venue_version':twin['venue_version'],'twin_sha256':h,'metric_twin':twin}
    @app.post('/optimize',response_model=OptimizationResponse)
    def optimize(request:Optimize):return service.optimize(request)
    @app.get('/twins/{venue_id}/versions/{version}',response_model=TwinReceipt)
    def get_twin(venue_id:str,version:int):
        with service.store.connection() as db:row=db.execute('SELECT sha FROM twins WHERE venue_id=? AND version=?',(venue_id,version)).fetchone()
        if not row:raise ResearchError('REVIEWED_TWIN_NOT_REGISTERED')
        twin=service.store.twin(venue_id,version,row['sha'])
        return {'venue_id':venue_id,'venue_version':version,'twin_sha256':row['sha'],'metric_twin':twin}
    @app.get('/runs/{run_id}',response_model=StoredRun)
    def get_run(run_id:str):return service.store.run(run_id)
    @app.get('/runs',response_model=RunIndex)
    def list_runs():
        with service.store.connection() as db:rows=db.execute('SELECT run_id,status,response_sha FROM runs ORDER BY rowid DESC LIMIT 100').fetchall()
        return {'runs':[dict(r) for r in rows]}
    @app.post('/runs/{run_id}/approve',response_model=ApprovalReceipt)
    def approve(run_id:str,request:Approve):return service.store.approve(run_id,request)
    @app.post('/approvals/{approval_id}/revoke',response_model=RevocationReceipt)
    def revoke(approval_id:str,request:Revoke):return service.store.revoke(approval_id,request.model_dump())
    @app.get('/contracts')
    def contracts():
        from pydantic import TypeAdapter
        from analysis_api import Analyze
        return {'api_version':'1.1.0','reviewed_twin':TwinReview.model_json_schema(),'registration':Register.model_json_schema(),'analysis':Analyze.model_json_schema(),'optimization':Optimize.model_json_schema(),'approval':Approve.model_json_schema(),'revocation':Revoke.model_json_schema(),'optimization_response':TypeAdapter(OptimizationResponse).json_schema(),'stored_run':StoredRun.model_json_schema()}
    return app
