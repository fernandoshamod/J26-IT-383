from lab import *
events=guard()
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
s=read(H/'MEASURED_SUMMARY.json');(H/'figures').mkdir(exist_ok=True)
fig,axes=plt.subplots(1,3,figsize=(16,5.4))
styles={'NEW':('#111111','-','o'),'B5':('#b45e14','--','x'),'B3':('#487a99',':','s'),'B0':('#777777','-.','.'),'B1':('#888888',':','^'),'B4':('#559477','--','+'),'B6':('#999999','-',None)}
for method,(color,line,marker) in styles.items():
 vals=[r for r in s if r['method']==method]
 for ax,key in zip(axes,['loss_mean','review_cost_mean','qualified_coverage']):
  ax.plot([r['budget'] for r in vals],[r[key] for r in vals],label=method,color=color,linestyle=line,marker=marker,linewidth=1.5)
for ax,title,ylabel in zip(axes,['Finite-world decision loss','Simulated facts actually reviewed','Actual qualified-result availability'],['Mean declared loss (dimensionless)','Mean unit-cost fact reviews (count)','Fraction of weighted worlds']):
 ax.set(title=title,xlabel='Requested review budget (unit-cost facts)',ylabel=ylabel,xticks=range(4));ax.grid(alpha=.15)
axes[1].legend(ncol=4,loc='lower center',bbox_to_anchor=(.5,-.47),frameon=False)
fig.suptitle('Controlled review sensitivity: ordinary task-aware B5 and NEW coincide',fontsize=14)
fig.subplots_adjust(left=.065,right=.985,top=.83,bottom=.31,wspace=.3)
fig.text(.06,.03,'Source: MEASURED_SUMMARY.json; four related cases × eight hypothetical worlds, one metric venue/seed.\nB0 averages all six review orders; B6 always costs 3 and exceeds budgets 0–2. Simulated priors/costs; no independent real-venue or human-benefit claim.',fontsize=9)
fig.savefig(H/'figures/REVIEW_TRADEOFFS.png',dpi=160);plt.close(fig)
worlds=read(H/'WORLD_INDEX.json');chosen=[w for w in worlds if w['case']=='ACTIVITY_GUEST_CHANGE' and w['bits'] in [[0,0],[1,1]]]
fig,axes=plt.subplots(1,2,figsize=(12,6.2))
for ax,w in zip(axes,chosen):
 r=read(w['result']);packet=read(w['input']);l=min(r['candidate_layouts'],key=lambda x:x['objective_metrics']['mean_stage_distance_m']);boundary=packet['scene']['venue']['boundary_m']
 ax.add_patch(Patch(boundary,closed=True,fill=False,edgecolor='#222222',linewidth=1.5))
 for z in l['zones']:
  if z['exclusive']:ax.add_patch(Patch(z['footprint_m'],closed=True,facecolor='#dfd7bd',edgecolor='#ac9e76',alpha=.7))
 for o in l['objects']:
  color={'stage':'#445e76','buffet_counter':'#b28354','round_table':'#679183','chair':'#c8d7d0','restricted_zone':'#999999'}.get(o['class'],'#999999')
  ax.add_patch(Patch(o['footprint_coordinates_m'],closed=True,facecolor=color,edgecolor='#333333',linewidth=.3))
 ax.set(xlim=(-1,33),ylim=(-1,25),xlabel='x (m)',ylabel='y (m)',title=f"Spatial interpretation {w['bits']}; {len(l['objects'])} objects\nActual best-stage returned candidate: {l['objective_metrics']['mean_stage_distance_m']:.3f} m")
 ax.set_aspect('equal')
fig.suptitle('Actual 96-guest controlled NSGA-II outputs: optional dance/obstacle interpretations',fontsize=12)
fig.subplots_adjust(bottom=.19,top=.84,wspace=.22)
fig.text(.08,.035,'Source: worlds/ACTIVITY_GUEST_CHANGE/{00,11}/ACTUAL_SEARCH/RESULT.json. Each search used 1200 evaluations.\nGrey: fixed reservation; tan: exclusive function/access zones; blue: stage; brown: buffet; green: returned tables/chairs.\nExplicitly simulated reviewed metric scene; source drawing anchors are not the physical geometry.',fontsize=9)
fig.savefig(H/'figures/CONTROLLED_ALTERNATIVES.png',dpi=160);plt.close(fig)
save('FIGURE_PROVENANCE.json',dict(summary_sha256=sha(H/'MEASURED_SUMMARY.json'),files={p.name:sha(p) for p in (H/'figures').glob('*.png')},world_paths=[w['result'] for w in chosen],guard=events))
