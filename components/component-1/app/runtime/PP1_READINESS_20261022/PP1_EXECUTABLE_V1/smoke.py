from support import PACKAGE,save
from fastapi.testclient import TestClient
from api import create_app
from fixtures import controlled_registration,optimization,approval,revise
def main():
    out=PACKAGE/'outputs/SMOKE';out.mkdir(parents=True);app=create_app(out/'runs.sqlite3');c=TestClient(app)
    reg=controlled_registration(out/'fixture');r=c.post('/twins',json=reg);print('register',r.status_code,flush=True);assert r.status_code==200,r.text
    twin=r.json();save(out/'REGISTER_REQUEST.json',reg);save(out/'REGISTER_RESPONSE.json',twin);req=optimization(twin);r=c.post('/optimize',json=req);print('initial',r.status_code,flush=True);response=r.json();save(out/'INITIAL_REQUEST.json',req);save(out/'INITIAL_RESPONSE.json',response);assert response['status']=='success',response
    a=c.post('/runs/'+response['run_id']+'/approve',json=approval(response));assert a.status_code==200,a.text;rev=revise(response,a.json(),req);r=c.post('/optimize',json=rev);print('adaptive',r.status_code,flush=True);save(out/'ADAPTIVE_REQUEST.json',rev);save(out/'ADAPTIVE_RESPONSE.json',r.json());assert r.json()['status']=='success',r.text
    print('alternatives',len(response['candidate_layouts']),len(r.json()['candidate_layouts']),flush=True)
if __name__=='__main__':main()
