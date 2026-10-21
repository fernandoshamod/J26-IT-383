"""Scientific figures from executed outputs; no illustration or optimizer."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from runtime import *

out=HERE/'outputs/FIGURES_FINAL';out.mkdir(parents=True,exist_ok=False);base=HERE/'outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017';ref=read(HERE/'outputs/CLOSEOUT_FINAL/REFERENCE_EAG_V32_S20261017.json');actual=read(base/'authorized_singleton_repair/EAG/RESULT.json');new=max(actual['candidate_layouts'],key=lambda l:actual['validation'][l['layout_id']]['stable_group_relocation_m']);target=read(base/'authorized_singleton_repair/INPUT.json')['context']['requested_group'];fig,axes=plt.subplots(1,2,figsize=(12,6))
for ax,layout,title in zip(axes,[ref['layout'],new],['Actual approved controlled reference','Actual returned singleton alternative']):
    x,y=zip(*ref['request']['venue']['boundary_m']);ax.plot(x,y,color='black')
    for ob in layout['objects']:ax.add_patch(Patch(ob['footprint_coordinates_m'],facecolor='#2e8390' if ob['group_id']==target else '#a7afb5',edgecolor='white',linewidth=.3))
    for z in layout['zones']:
        if z['exclusive']:ax.add_patch(Patch(z['footprint_m'],fill=False,hatch='///',edgecolor='#745e76'))
    ax.set_aspect('equal');ax.autoscale_view();ax.set_title(title);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
x,y=ref['layout']['group_centers_m'][target];nx,ny=new['group_centers_m'][target];axes[1].annotate('',xy=(nx,ny),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='black'))
fig.suptitle('Actual authorized singleton repair: all other individual geometry remains locked')
fig.text(.5,.045,'Largest-relocation returned option shown for inspection; arrow is endpoint displacement, not a validated transport route.',ha='center',fontsize=9)
fig.text(.5,.018,'Source: EXPERIMENT_FINAL / VENUE_32_24_SEED_20261017; 1680 actual evaluations. Explicit simulated authority only.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.09,1,.94));fig.savefig(out/'ACTUAL_SINGLETON_REPAIR.png',dpi=160);plt.close(fig)
ag=read(HERE/'outputs/CLOSEOUT_FINAL/AGGREGATES.json');fig,axes=plt.subplots(1,2,figsize=(11,4.5));names=[a['method'] for a in ag]
for ax,key,title in zip(axes,['actual_search_evaluations','dirty_graph_nodes_total'],['Actual scenario search evaluations','Dirty graph nodes (metadata, not skipped validation)']):
    vals=[a[key] for a in ag];ax.bar(names,vals,color='#527f89');ax.set_ylim(0,max(vals)*1.18);ax.set_title(title,fontsize=10);ax.set_ylabel('Count')
    for i,v in enumerate(vals):ax.text(i,v,str(v),ha='center',va='bottom')
fig.suptitle('No EAG-exclusive optimizer or dependency-tracking advantage in this test')
fig.text(.5,.02,'Source: CLOSEOUT_FINAL/AGGREGATES.json. All methods: zero false decisions/protected changes; full candidate verification retained.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.07,1,.93));fig.savefig(out/'MEASURED_BASELINE_COMPARISON.png',dpi=160);plt.close(fig)
