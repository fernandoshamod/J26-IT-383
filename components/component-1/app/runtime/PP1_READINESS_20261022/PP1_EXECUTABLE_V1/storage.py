import sqlite3,json,uuid
from pathlib import Path
from support import digest,filehash,ResearchError
class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS twins(venue_id TEXT,version INTEGER,sha TEXT,body TEXT,PRIMARY KEY(venue_id,version));
            CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,status TEXT,request_json TEXT,response_json TEXT,response_sha TEXT);
            CREATE TABLE IF NOT EXISTS approvals(approval_id TEXT PRIMARY KEY,run_id TEXT,layout_id TEXT,layout_sha TEXT,venue_id TEXT,venue_version INTEGER,twin_sha TEXT,status TEXT,review_json TEXT);
            CREATE TABLE IF NOT EXISTS approval_events(event_id TEXT PRIMARY KEY,approval_id TEXT,event TEXT,record_json TEXT);''')
    def connection(self):
        c=sqlite3.connect(self.path,timeout=30);c.row_factory=sqlite3.Row;return c
    def register(self,twin):
        h=digest(twin)
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM twins WHERE venue_id=? AND version=?',(twin['venue_id'],twin['venue_version'])).fetchone()
            if old:
                if old['sha']!=h:raise ResearchError('VENUE_VERSION_CONTENT_CHANGED')
                return h
            latest=c.execute('SELECT MAX(version) FROM twins WHERE venue_id=?',(twin['venue_id'],)).fetchone()[0]
            if latest is not None and twin['venue_version']<=latest:raise ResearchError('VENUE_VERSION_NOT_MONOTONIC')
            c.execute('INSERT INTO twins VALUES(?,?,?,?)',(twin['venue_id'],twin['venue_version'],h,json.dumps(twin,allow_nan=False)))
        return h
    def twin(self,venue,version,h):
        with self.connection() as c:
            latest=c.execute('SELECT MAX(version) FROM twins WHERE venue_id=?',(venue,)).fetchone()[0]
            row=c.execute('SELECT * FROM twins WHERE venue_id=? AND version=?',(venue,version)).fetchone()
        if row is None:raise ResearchError('REVIEWED_TWIN_NOT_REGISTERED')
        if latest!=version:raise ResearchError('STALE_VENUE_VERSION',{'current_version':latest})
        if row['sha']!=h:raise ResearchError('TWIN_HASH_MISMATCH')
        body=json.loads(row['body'])
        if digest(body)!=row['sha']:raise ResearchError('STORED_TWIN_CONTENT_CORRUPTED')
        return body
    def save_run(self,request,response):
        run_id=response['run_id'];body=json.dumps(response,allow_nan=False);h=digest(response)
        with self.connection() as c:
            if response['status']=='success':
                # Serialize final freshness check with the write. A review/version
                # revoked while NSGA-II ran must not become a saved success.
                c.execute('BEGIN IMMEDIATE')
                twin=c.execute('SELECT version,sha,body FROM twins WHERE venue_id=? ORDER BY version DESC LIMIT 1',(request['venue_id'],)).fetchone()
                if not twin or twin['version']!=request['venue_version'] or twin['sha']!=request['twin_sha256'] or digest(json.loads(twin['body']))!=twin['sha']:raise ResearchError('TWIN_CHANGED_DURING_EXECUTION')
                metric=json.loads(twin['body'])
                if not Path(metric['source']['path']).is_file() or filehash(metric['source']['path'])!=metric['source']['sha256']:raise ResearchError('SOURCE_CHANGED_DURING_EXECUTION')
                from evidence import verify_evidence_artifacts
                verify_evidence_artifacts(metric['review_record'])
                reference=request.get('reference')
                if reference:
                    approved=c.execute('SELECT * FROM approvals WHERE approval_id=?',(reference['approval_id'],)).fetchone()
                    if not approved or approved['status']!='approved' or approved['run_id']!=reference['run_id'] or approved['layout_id']!=reference['layout_id'] or approved['layout_sha']!=reference['layout_sha256']:raise ResearchError('REFERENCE_REVOKED_OR_CHANGED_DURING_EXECUTION')
            c.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run_id,response['status'],json.dumps(request,allow_nan=False),body,h))
        return response
    def run(self,run_id):
        with self.connection() as c:row=c.execute('SELECT * FROM runs WHERE run_id=?',(run_id,)).fetchone()
        if not row:raise ResearchError('RUN_NOT_FOUND')
        response=json.loads(row['response_json'])
        if digest(response)!=row['response_sha']:raise ResearchError('STORED_RESPONSE_CORRUPTED')
        request=json.loads(row['request_json'])
        if response.get('xai',{}).get('request_sha256')!=digest(request):raise ResearchError('STORED_REQUEST_CORRUPTED')
        return dict(request=request,response=response)
    def approve(self,run_id,approval):
        stored=self.run(run_id);response=stored['response'];req=stored['request']
        if response['status']!='success':raise ResearchError('CANNOT_APPROVE_NON_SUCCESS')
        self.twin(req['venue_id'],approval.venue_version,req['twin_sha256'])
        if approval.venue_version!=req['venue_version']:raise ResearchError('APPROVAL_VENUE_VERSION_MISMATCH')
        layout=next((l for l in response['candidate_layouts'] if l['layout_id']==approval.layout_id),None)
        if not layout or digest(layout)!=approval.layout_sha256:raise ResearchError('APPROVAL_LAYOUT_HASH_MISMATCH')
        expected='SIMULATED_FIXTURE_REVIEW' if response['source_domain']=='controlled_synthetic' else 'EXTERNAL_RESEARCH_REVIEW'
        if approval.scope!=expected:raise ResearchError('APPROVAL_SCOPE_MISMATCH')
        aid=uuid.uuid4().hex
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            latest=c.execute('SELECT version,sha FROM twins WHERE venue_id=? ORDER BY version DESC LIMIT 1',(req['venue_id'],)).fetchone()
            if not latest or latest['version']!=req['venue_version'] or latest['sha']!=req['twin_sha256']:raise ResearchError('TWIN_CHANGED_DURING_APPROVAL')
            c.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?)',(aid,run_id,approval.layout_id,approval.layout_sha256,req['venue_id'],req['venue_version'],req['twin_sha256'],'approved',json.dumps(approval.model_dump(),allow_nan=False)))
            c.execute('INSERT INTO approval_events VALUES(?,?,?,?)',(uuid.uuid4().hex,aid,'approved',json.dumps(approval.model_dump())))
        return dict(approval_id=aid,status='approved',approval_origin='EXPLICIT_LOCAL_INPUT_NOT_AUTHENTICATED')
    def reference(self,ref,request):
        with self.connection() as c:row=c.execute('SELECT * FROM approvals WHERE approval_id=?',(ref.approval_id,)).fetchone()
        if not row or row['status']!='approved':raise ResearchError('REFERENCE_NOT_APPROVED')
        expected=(ref.run_id,ref.layout_id,ref.layout_sha256,request.venue_id,request.venue_version,request.twin_sha256)
        actual=tuple(row[k] for k in ['run_id','layout_id','layout_sha','venue_id','venue_version','twin_sha'])
        if actual!=expected:raise ResearchError('STALE_OR_UNRELATED_REFERENCE')
        stored=self.run(ref.run_id);layout=next((l for l in stored['response']['candidate_layouts'] if l['layout_id']==ref.layout_id),None)
        if layout is None or digest(layout)!=ref.layout_sha256:raise ResearchError('REFERENCE_LAYOUT_CORRUPTED')
        return layout,stored['request']
    def revoke(self,aid,record):
        with self.connection() as c:
            row=c.execute('SELECT approval_id FROM approvals WHERE approval_id=?',(aid,)).fetchone()
            if not row:raise ResearchError('APPROVAL_NOT_FOUND')
            c.execute("UPDATE approvals SET status='revoked' WHERE approval_id=?",(aid,))
            c.execute('INSERT INTO approval_events VALUES(?,?,?,?)',(uuid.uuid4().hex,aid,'revoked',json.dumps(record)))
        return dict(approval_id=aid,status='revoked')
