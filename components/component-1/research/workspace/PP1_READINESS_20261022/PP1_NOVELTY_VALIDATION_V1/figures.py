from lab import *
events=guard()
import matplotlib.pyplot as plt,numpy as np
from matplotlib.patches import Polygon as Patch
raw=read(H/'RAW_EXPERIMENT_RESULTS.json');methods=['B0','B1','B2','B3','B4','EAG'];cases=list(read(H/'EXPERIMENT_CONFIGURATION.json')['expectations']);out=H/'figures_v2';out.mkdir(exist_ok=False)
matrix=np.array([[sum(r['evaluations'] for r in raw if r['method']==m and r['case']==c) for c in cases] for m in methods])
fig,ax=plt.subplots(figsize=(15,6));im=ax.imshow(matrix,aspect='auto',cmap='Blues');ax.set_yticks(range(6),methods);ax.set_xticks(range(len(cases)),[c.replace('_','\n') for c in cases],fontsize=7);ax.set_title('Actual objective evaluations summed across four controlled units')
for i in range(6):
 for j in range(len(cases)):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=7,color='white' if matrix[i,j]>matrix.max()/2 else 'black')
fig.colorbar(im,ax=ax,label='Objective evaluations');fig.text(.02,.015,'Zero can mean reuse, refusal, unsupported comparison or initialization failure. Consult raw statuses; no algorithmic speedup inferred.',fontsize=9);fig.tight_layout(rect=(0,.07,1,1));fig.savefig(out/'MEASURED_EVALUATIONS.png',dpi=160);plt.close(fig)
pairs=[p for p in read(H/'PAIRED_DIFFERENCES.json') if p['both_eligible']];fig,ax=plt.subplots(figsize=(10,4));ax.scatter(range(len(pairs)),[p['best_stage_difference'] for p in pairs],color='#125a70');ax.axhline(0,color='grey',lw=1);ax.set_ylim(-.01,.01);ax.set_xlabel('Paired eligible unit/case (correlated technical repeats)');ax.set_ylabel('EAG minus B4 best mean stage distance (m)');ax.set_title('Strong conventional wrapper challenge: measured paired quality differences');fig.tight_layout();fig.savefig(out/'PAIRED_STAGE_DIFFERENCES.png',dpi=160);plt.close(fig)
r=next(x for x in raw if x['method']=='EAG' and x['case']=='authorized_singleton_repair');response=read(r['response_path']);ref=read(H/'inputs'/r['unit']/'REFERENCE.json')['layout'];target=read(Path(r['response_path']).parent/'INPUT.json')['context']['requested_group'];chosen=min(response['candidate_layouts'],key=lambda l:l['search_objectives']['target_stage_distance_m'])
fig,axes=plt.subplots(1,2,figsize=(13,5.5))
for ax,layout,title in zip(axes,[ref,chosen],['Verified reference','Actual authorized singleton output']):
 for ob in layout['objects']:
  color='#ee8c35' if ob['group_id']==target else '#728c95' if ob['group_id'] else '#254e70'
  ax.add_patch(Patch(ob['footprint_coordinates_m'],closed=True,facecolor=color,edgecolor='white',lw=.3,alpha=.85))
 ax.set(xlim=(0,32),ylim=(0,24),xlabel='metres',ylabel='metres',title=title);ax.set_aspect('equal');ax.grid(alpha=.15)
fig.suptitle('Actual returned metric polygons; orange = explicitly movable target, other objects locked');fig.text(.02,.02,'Controlled registered venue and simulated authority; no real-venue validation or genuine human approval. Selected by actual target-stage objective.',fontsize=9);fig.tight_layout(rect=(0,.14,1,.95));fig.savefig(out/'ACTUAL_SINGLETON_REPAIR.png',dpi=160);plt.close(fig)
save('FIGURE_PROVENANCE_V2.json',dict(raw_results_sha256=sha(H/'RAW_EXPERIMENT_RESULTS.json'),singleton_response=r['response_path'],singleton_response_sha256=sha(r['response_path']),selected_layout_sha256=digest(chosen),target_group=target,figures={p.name:sha(p) for p in out.glob('*.png')},previous_figure_version_retained='figures/; first singleton footer overlapped axis labels; no data change',guard=events))
print('Three measured/actual-polygon scientific figures saved')
