"""Additive local layout-edit validator. It never rewrites backend run records."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import Polygon
import uvicorn

class EditRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    run_id:str=Field(min_length=32,max_length=32)
    layout_id:str=Field(min_length=1)
    group_id:str=Field(min_length=1)
    delta_m:list[float]=Field(min_length=2,max_length=2)
    reviewer_id:str=Field(min_length=1,max_length=200)
    reason:str=Field(min_length=5,max_length=1000)
    explicit_permission:bool

class EventProjectRecord(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,populate_by_name=True)
    id:str=Field(min_length=1,max_length=100)
    schema_:str=Field(alias='schema',pattern='^COMPONENT1_EVENT_PROJECTS_V1$')
    name:str=Field(max_length=120)
    type:str=Field(pattern='^(Wedding|Birthday|Corporate|Conference|Musical Show)$')
    date:str=Field(max_length=10)
    startTime:str=Field(max_length=5)
    endTime:str=Field(max_length=5)
    venue:str=Field(max_length=180)
    guests:int=Field(ge=1,le=100000)
    budget:float|None=Field(default=None,ge=0,le=1000000000)
    venueMode:str=Field(pattern='^(indoor|outdoor|hybrid)$')
    clientRequirements:str=Field(max_length=2000)
    plannerNotes:str=Field(max_length=2000)
    status:str=Field(pattern='^(draft|review_pending|active|completed|archived)$')
    analysisId:str|None=None
    twinId:str|None=None
    twinVersion:int|None=Field(default=None,ge=1)
    runIds:list[str]=Field(default_factory=list,max_length=1000)
    createdAt:str=Field(min_length=1,max_length=64)
    updatedAt:str=Field(min_length=1,max_length=64)

class Service:
    def __init__(self,db:Path,backend:str):
        self.db=db;self.backend=backend.rstrip('/');self.db.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.db) as c:
            c.execute('CREATE TABLE IF NOT EXISTS layout_edit_drafts (draft_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, layout_id TEXT NOT NULL, group_id TEXT NOT NULL, source_sha256 TEXT NOT NULL, venue_id TEXT NOT NULL, venue_version INTEGER NOT NULL, twin_sha256 TEXT NOT NULL, baseline_layout_sha256 TEXT NOT NULL, request_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS event_projects (project_id TEXT PRIMARY KEY, body_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS event_projects_updated_idx ON event_projects(updated_at DESC)')
    def list_event_projects(self)->list[dict[str,Any]]:
        with sqlite3.connect(self.db) as c:
            rows=c.execute('SELECT body_json FROM event_projects ORDER BY updated_at DESC, project_id').fetchall()
        return [json.loads(row[0]) for row in rows]
    def get_event_project(self,project_id:str)->dict[str,Any]|None:
        with sqlite3.connect(self.db) as c:
            row=c.execute('SELECT body_json FROM event_projects WHERE project_id=?',(project_id,)).fetchone()
        return json.loads(row[0]) if row else None
    def create_event_project(self,project:EventProjectRecord)->dict[str,Any]:
        value=project.model_dump(mode='json',by_alias=True);raw=json.dumps(value,separators=(',',':'),allow_nan=False)
        try:
            with sqlite3.connect(self.db) as c:
                c.execute('INSERT INTO event_projects(project_id,body_json,created_at,updated_at) VALUES (?,?,?,?)',(value['id'],raw,value['createdAt'],value['updatedAt']))
        except sqlite3.IntegrityError as e: raise HTTPException(409,detail={'reason':'EVENT_PROJECT_ALREADY_EXISTS','id':value['id']}) from e
        return value
    def update_event_project(self,project_id:str,project:EventProjectRecord)->dict[str,Any]:
        value=project.model_dump(mode='json',by_alias=True)
        if value['id']!=project_id: raise HTTPException(422,detail={'reason':'EVENT_PROJECT_ID_MISMATCH'})
        raw=json.dumps(value,separators=(',',':'),allow_nan=False)
        with sqlite3.connect(self.db) as c:
            cur=c.execute('UPDATE event_projects SET body_json=?,updated_at=? WHERE project_id=?',(raw,value['updatedAt'],project_id))
            if cur.rowcount!=1: raise HTTPException(404,detail={'reason':'EVENT_PROJECT_NOT_FOUND','id':project_id})
        return value
    def delete_event_project(self,project_id:str)->None:
        with sqlite3.connect(self.db) as c:
            cur=c.execute('DELETE FROM event_projects WHERE project_id=?',(project_id,))
            if cur.rowcount!=1: raise HTTPException(404,detail={'reason':'EVENT_PROJECT_NOT_FOUND','id':project_id})
    def get(self,path:str)->dict[str,Any]:
        req=urllib.request.Request(self.backend+path,headers={'Accept':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read())
        except Exception as e: raise HTTPException(502,detail={'reason':'FROZEN_BACKEND_READ_FAILED','details':str(e)})
    def validate(self,q:EditRequest)->dict[str,Any]:
        if not q.explicit_permission: raise HTTPException(422,detail={'reason':'EXPLICIT_EDIT_PERMISSION_REQUIRED'})
        run=self.get('/runs/'+q.run_id); response=run.get('response')
        if not isinstance(response,dict) or response.get('status')!='success': raise HTTPException(422,detail={'reason':'SOURCE_RUN_NOT_SUCCESS'})
        if response.get('run_id')!=q.run_id: raise HTTPException(409,detail={'reason':'RUN_ID_MISMATCH'})
        original=next((x for x in response.get('candidate_layouts',[]) if x.get('layout_id')==q.layout_id),None)
        if original is None: raise HTTPException(404,detail={'reason':'LAYOUT_NOT_IN_SOURCE_RUN'})
        cert=response.get('verification',{}).get(q.layout_id,{})
        if not cert.get('valid') or not cert.get('layout_sha256'): raise HTTPException(422,detail={'reason':'BASE_LAYOUT_NOT_INDEPENDENTLY_VERIFIED'})
        objects=original.get('objects',[]); selected=[o for o in objects if o.get('group_id')==q.group_id]
        if not selected or any(o.get('class') not in {'round_table','chair'} for o in selected): raise HTTPException(422,detail={'reason':'GROUP_NOT_EDITABLE','details':'Only an existing seating group of tables/chairs can be translated.'})
        if q.group_id in response.get('verification',{}).get(q.layout_id,{}).get('locked_group_ids',[]): raise HTTPException(422,detail={'reason':'GROUP_LOCKED_IN_BASE_LAYOUT'})
        dx,dy=q.delta_m
        if abs(dx)+abs(dy)<1e-9: raise HTTPException(422,detail={'reason':'ZERO_MOVEMENT'})
        moved=[]; source_hash=response.get('source_image_sha256')
        for o in objects:
            z=dict(o)
            if o.get('group_id')==q.group_id:
                z['footprint_coordinates_m']=[[float(p[0])+dx,float(p[1])+dy] for p in o['footprint_coordinates_m']]
            moved.append(z)
        boundary=Polygon(response['actual_boundary_polygon_m'])
        polys=[]
        for obj in moved:
            p=Polygon(obj['footprint_coordinates_m'])
            if not p.is_valid or p.area<=0: raise HTTPException(422,detail={'reason':'INVALID_POLYGON','details':obj.get('object_id')})
            if not boundary.covers(p): raise HTTPException(422,detail={'reason':'OUTSIDE_USABLE_BOUNDARY','details':obj.get('object_id')})
            polys.append((obj,p))
        minimum=float(response.get('resolved_requirements',{}).get('minimum_clearance_m',0.0))
        min_pair=None;min_clearance=float('inf')
        for i,(a,pa) in enumerate(polys):
            for b,pb in polys[i+1:]:
                area=pa.intersection(pb).area
                if area>1e-8: raise HTTPException(422,detail={'reason':'OBJECT_OVERLAP','details':[a['object_id'],b['object_id']]})
                if a.get('group_id')!=b.get('group_id'):
                    d=pa.distance(pb)
                    if d<min_clearance: min_clearance=d;min_pair=[a['object_id'],b['object_id']]
        if min_clearance+1e-8<minimum: raise HTTPException(422,detail={'reason':'MINIMUM_CLEARANCE_VIOLATION','details':{'required_m':minimum,'observed_m':min_clearance,'objects':min_pair}})
        draft_id=uuid.uuid4().hex
        result={'schema':'LOCAL_LAYOUT_EDIT_DRAFT_V1','status':'validated_draft','draft_id':draft_id,'run_id':q.run_id,'layout_id':q.layout_id,'group_id':q.group_id,'delta_m':[dx,dy],'layout_objects':moved,'verification':{'valid':True,'boundary_containment':True,'positive_area_overlaps':0,'minimum_clearance_required_m':minimum,'minimum_clearance_observed_m':None if min_clearance==float('inf') else min_clearance,'translated_objects':len(selected),'fixed_and_other_objects_unchanged':True},'source_image_sha256':source_hash,'venue_id':response.get('venue_id'),'venue_version':response.get('venue_version'),'twin_sha256':response.get('twin_sha256'),'baseline_layout_sha256':cert['layout_sha256'],'reviewer_id':q.reviewer_id,'reason':q.reason,'approval_scope':'LOCAL_DRAFT_NOT_AUTHENTICATED_PLANNER_APPROVAL','persisted_to_frozen_run_history':False,'created_at':datetime.now(timezone.utc).isoformat()}
        raw=json.dumps(result,separators=(',',':'),allow_nan=False)
        with sqlite3.connect(self.db) as c:c.execute('INSERT INTO layout_edit_drafts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(draft_id,q.run_id,q.layout_id,q.group_id,source_hash,response.get('venue_id'),response.get('venue_version'),response.get('twin_sha256'),cert['layout_sha256'],q.model_dump_json(),raw,result['created_at']))
        return result
    def history(self,run_id:str)->list[dict[str,Any]]:
        with sqlite3.connect(self.db) as c:rows=c.execute('SELECT result_json FROM layout_edit_drafts WHERE run_id=? ORDER BY created_at DESC',(run_id,)).fetchall()
        return [json.loads(x[0]) for x in rows]

def create_app(db:Path,backend:str)->FastAPI:
    service=Service(db,backend);app=FastAPI(title='Component 1 additive layout edit validator',version='1.0.0')
    @app.get('/health')
    def health():return {'status':'ok','version':'1.0.0','backend':service.backend,'authority':'local unauthenticated research companion','sqlite_event_crud':True}
    @app.get('/event-projects')
    def list_event_projects():return {'projects':service.list_event_projects(),'storage':'local_sqlite'}
    @app.get('/event-projects/{project_id}')
    def get_event_project(project_id:str):
        value=service.get_event_project(project_id)
        if value is None: raise HTTPException(404,detail={'reason':'EVENT_PROJECT_NOT_FOUND','id':project_id})
        return {'project':value,'storage':'local_sqlite'}
    @app.post('/event-projects',status_code=201)
    def create_event_project(project:EventProjectRecord):return {'project':service.create_event_project(project),'storage':'local_sqlite'}
    @app.put('/event-projects/{project_id}')
    def update_event_project(project_id:str,project:EventProjectRecord):return {'project':service.update_event_project(project_id,project),'storage':'local_sqlite'}
    @app.delete('/event-projects/{project_id}',status_code=204)
    def delete_event_project(project_id:str):service.delete_event_project(project_id);return None
    @app.post('/layout-edits/validate')
    def validate_edit(q:EditRequest):return service.validate(q)
    @app.get('/layout-edits/{run_id}')
    def edit_history(run_id:str):return {'run_id':run_id,'drafts':service.history(run_id)}
    return app

def main():
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--backend',default='http://127.0.0.1:8765');p.add_argument('--port',type=int,default=8768);a=p.parse_args()
    uvicorn.run(create_app(Path(a.db),a.backend),host='127.0.0.1',port=a.port,log_level='info')
if __name__=='__main__':main()
