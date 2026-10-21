"""Repeatable controlled demonstration. All review decisions are simulated."""
import copy
from pathlib import Path
from fastapi.testclient import TestClient
from support import save,read
from api import create_app
from fixtures import controlled_registration,optimization,approval,revise

def plot_response(response,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    selected=next(l for l in response['candidate_layouts'] if l['layout_id']==response['selected_layout_id'])
    fig,ax=plt.subplots(figsize=(11,8))
    boundary=response['actual_boundary_polygon_m'];ax.plot(*zip(*boundary),color='black',lw=2)
    for ob in selected['objects']:
        points=ob['footprint_coordinates_m'];kind=ob['class']
        ax.add_patch(Patch(points,facecolor={'chair':'#81b4d5','round_table':'#f4bc61','stage':'#ac99c8'}.get(kind,'#aaaaaa'),edgecolor='#333333',linewidth=.35))
    for gid,xy in selected['group_centers_m'].items():ax.text(*xy,gid.rsplit('_',1)[-1],fontsize=6,ha='center')
    ax.set_aspect('equal');ax.autoscale_view();ax.set_xlabel('metres');ax.set_ylabel('metres')
    ax.set_title(f"CONTROLLED SYNTHETIC — {response['source_domain']}\n{len(selected['objects'])} objects | {len(response['candidate_layouts'])} verified alternatives")
    fig.tight_layout();fig.savefig(out,dpi=160);plt.close(fig)

def run_demo(destination):
    out=Path(destination);out.mkdir(parents=True,exist_ok=False)
    client=TestClient(create_app(out/'research.sqlite3'))
    reg=controlled_registration(out/'fixture');save(out/'REGISTER_REQUEST.json',reg)
    registered=client.post('/twins',json=reg);assert registered.status_code==200,registered.text
    save(out/'REGISTER_RESPONSE.json',registered.json());req=optimization(registered.json())
    initial=client.post('/optimize',json=req).json();assert initial['status']=='success',initial
    save(out/'INITIAL_REQUEST.json',req);save(out/'INITIAL_RESPONSE.json',initial);plot_response(initial,out/'INITIAL_LAYOUT.png')
    ar=approval(initial);approved=client.post('/runs/'+initial['run_id']+'/approve',json=ar);assert approved.status_code==200,approved.text
    save(out/'SIMULATED_APPROVAL_REQUEST.json',ar);save(out/'SIMULATED_APPROVAL_RESPONSE.json',approved.json())
    rev=revise(initial,approved.json(),req);adaptive=client.post('/optimize',json=rev).json();assert adaptive['status']=='success',adaptive
    save(out/'ADAPTIVE_REQUEST.json',rev);save(out/'ADAPTIVE_RESPONSE.json',adaptive);plot_response(adaptive,out/'ADAPTIVE_LAYOUT.png')
    denied=copy.deepcopy(rev);denied['permissions']=[];denial=client.post('/optimize',json=denied).json();assert denial['status']!='success' and denial['optimizer_evaluations']==0
    save(out/'DENIED_REQUEST.json',denied);save(out/'DENIED_RESPONSE.json',denial)
    save(out/'RUN_INDEX.json',client.get('/runs').json())
    save(out/'DEMO_SUMMARY.json',{'domain':'controlled_synthetic','real_review_claimed':False,'initial_alternatives':len(initial['candidate_layouts']),'adaptive_alternatives':len(adaptive['candidate_layouts']),'denial':denial['reason'],'sqlite_persistence':True})
    print('Controlled initial/adaptive layouts and persisted denial:',out.resolve())
