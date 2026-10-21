"""Generate bounded acceptance from actual saved evidence, never invented metrics."""
from common import *
import csv,collections,platform,importlib.metadata
H.joinpath('reports').mkdir(exist_ok=True)
evaluation=read(H/'objects_v2/EVALUATION.json');parts=read(H/'objects_v2/SPLITS.json');prep=read(H/'objects_v2/PREPARATION.json');frozen=read(H/'objects_v2/CHECKPOINT_FREEZE.json')
ontology=read(H/'ONTOLOGY_FREEZE.json')['event_classes'];definitions=[
 'Dedicated bar-service counter; requires explicit role annotation, not every countertop.',
 'Food-service buffet unit; generic rectangular table is not adequate evidence.',
 'Individual top-view seat including published ordinary/bar chairs; exclude sofas and grouped seating-row targets. Drawing content is not physical stock.',
 'Explicitly designated dance activity region; empty room is not evidence.',
 'Explicit exhibition/display booth instance; not arbitrary room or partition enclosure.',
 'Explicit lectern/podium instance; not an interchangeable stage or cabinet.',
 'Individual rectangular tabletop; source table labels/boxes enclosing chairs do not establish this exact object.',
 'Explicit check-in/registration desk role; cannot infer from generic desk appearance.',
 'Individual circular tabletop; room circle, sink and generic table category are insufficient.',
 'Explicit grouped row-of-seats annotation, not a relabelled single chair.',
 'Explicit performance-stage platform annotation; proposed design stage is not observed venue stock.',
 'Explicit movable/temporary divider annotation; cannot infer temporary status from a wall line.'
]
counts={s:collections.Counter(a['source_class_id'] for r in rr for a in r['annotations']) for s,rr in parts.items()}
class_rows=[]
for i,(name,definition) in enumerate(zip(ontology,definitions)):
 row={'frozen_id':i,'class':name,'visual_policy':definition,'source_mapping':'2DPlan13 bar chairs +18 chair' if i==2 else None,
 'train_instances':sum(counts['train'].values()) if i==2 else 0,'validation_instances':sum(counts['val'].values()) if i==2 else 0,'test_instances':sum(counts['test'].values()) if i==2 else 0,
 'status':'PUBLISHED_LABEL_AGREEMENT_PILOT_ONLY' if i==2 else 'NOT_VALIDATED','ap50':evaluation['results']['published_chair_pilot']['ap50'] if i==2 else None,
 'ap50_95':evaluation['results']['published_chair_pilot']['ap50_95'] if i==2 else None,'operating_precision025':evaluation['results']['published_chair_pilot']['operating025']['precision'] if i==2 else None,
 'operating_recall025':evaluation['results']['published_chair_pilot']['operating025']['recall'] if i==2 else None,'inventory_authority':'UNKNOWN; drawing symbols may describe proposed furnishing'}
 class_rows.append(row)
save('reports/ALL_TWELVE_CLASS_RESULTS.json',class_rows)
with (H/'reports/ALL_TWELVE_CLASS_RESULTS.csv').open('x',newline='',encoding='utf-8') as f:
 writer=csv.DictWriter(f,fieldnames=list(class_rows[0]));writer.writeheader();writer.writerows(class_rows)
outdoor=[{'class':c,'recognition_metric':None,'status':'NOT_EVALUATED','actual_implementation':'Source-bound native SCUT annotation import only, NOT learned prediction' if c=='entrance' else 'No qualified real-site-plan recognition path','eligible_original_raster_training_pairs':0} for c in read(H/'ONTOLOGY_FREEZE.json')['outdoor_classes']]
save('reports/ALL_OUTDOOR_CLASS_RESULTS.json',outdoor)
save('reports/SOURCE_CLASS_COUNTS.json',{s:dict(c) for s,c in counts.items()})
sources=[
 {'name':'2DPlan Object Detection v7','url':'https://universe.roboflow.com/real-workflow/2dplan-object-detection','actual_location':str(ROOT/'01_DATASET_DOWNLOADS/02_2DPlan_Objects'),'obtained':'Pre-existing local export, not newly downloaded','publisher_license':'CC BY4.0','drawing_copyright':'Original drawing-owner chain unverified; publisher declaration does not independently establish ownership','commercial':'Not cleared by this audit; do not extrapolate uploader licence to all original drawings','images_actual':2055,'publisher_banner_images':2058,'classes':40,'used':'One-class published chair-label reproduction pilot','counts':prep['stats'],'quality':'Known unlabelled visible chairs; full venue ancestry unavailable; mixed polygon/box labels','families':'Technical filename/byte/D4pHash groups only; physical source-family independence not established'},
 {'name':'Chair/Table Floor Plan Detection','url':'https://universe.roboflow.com/aiteam02/chair-table-floor-plan-detection','images_documented':62,'classes_documented':['chair-back-and-arm','chair-back-only','chair-stool','sofa-L-shape','sofa1','sofa2','sofa3','table-L-shape','table-rectangle','table-round'],'publisher_license':'CC BY4.0','drawing_copyright':'Unverified original sources','download':'Public export page returned403; no auth/security bypass or hosted inference','used':False,'family_identity':'Unknown'},
 {'name':'Floor Plan All Objects','url':'https://universe.roboflow.com/floor-plan-rendering-l4ax8/floor-plan-all-objects','images_documented':220,'class_count_documented':21,'publisher_license':'CC BY4.0','drawing_copyright':'Unverified original sources','download':'Public pages returned403 to acquisition client; web metadata readable','used':False,'mapping':'Generic/dinner/showcase/study tables not silently mapped to exact event roles/shapes'},
 {'name':'CubiCasa5K','url':'https://github.com/CubiCasa/CubiCasa5k','publisher_license':'CC BY-NC4.0','used':'Existing V3 structural/opening checkpoints read only; no repeated training','mapping':'Existing native fixed-furniture/Space Outdoor labels do not supply the required12event or7site ontology','images_documented':5000,'download':'Existing extraction reused'},
 {'name':'FloorPlanCAD','url':'https://floorplancad.github.io/','publisher_license':'Annotations CC BY-NC4.0; authors explicitly do not own drawing copyrights','drawing_copyright':'Separate rights unresolved; no new training use','local_svg_counts':{d.name:len(list(d.glob('*.svg'))) for d in (ROOT/'01_DATASET_DOWNLOADS/FloorPlanCAD').iterdir() if d.is_dir()},'qualification':'Local semantic-id/instance-id version not proven equivalent to current author semanticId taxonomy. V3 visual counterexamples retained. No guessed chair/table labels used.','used':False},
 {'name':'SCUT-AutoALP','url':'https://github.com/designfuturelab702/SCUT-AutoALP-Database-Release','publication':'https://doi.org/10.1587/transinf.2020EDL8076','publisher_license':'Academic research only','drawing_copyright':'Internet-collected originals; no commercial clearance','actual_local_campus_records':302,'original_campus_drawings_present':0,'files_used':'302layout/boundary label pairs hashed; ten native entrance annotation conversions checked','mapping':'Fig2 yellow entrance only. Site Range is not legal/usable boundary; other labels not silently mapped to event semantic targets.','new_model_training':False,'download':'Existing612MBarchive reused; current publisher README/Fig2/tree documentation acquired'},
 {'name':'NPS Yosemite orientation maps','url':'https://www.nps.gov/yose/planyourvisit/images/pinescombined.jpg','pdf_url':'https://www.nps.gov/yose/planyourvisit/upload/yosemitecampgroundmap2013.pdf','rights_url':'https://www.nps.gov/subjects/gisandmapping/data-sources-and-accuracy.htm','license':'NPS map public-domain statement; not a blanket licence for every NPS image','annotations':'No reviewed event/site ontology ground truth','used':'Real legend/distractor abstention and annotation queue, not positive boundary accuracy','limits':'Orientation map, not legal boundary survey'},
 {'name':'ResPlan','url':'https://github.com/m-agour/ResPlan','license':'Data CC BY4.0; code MIT','records_documented':17000,'used':False,'reason':'Vector/graph residential structure, no furniture; not corresponding site raster target data'},
 {'name':'FP4S','url':'https://doi.org/10.7910/DVN/MDIRHE','used':False,'records_documented':'558training images with25element scribble annotations','rights':'Archive/data-use conditions need separate reconciliation; source-image redistribution restricted','reason':'No qualified mapping/full instance labels for requested targets established; no download'},
 {'name':'AntPlan-270 / Architect-Ant','url':'https://arxiv.org/html/2606.10953v1','used':False,'records_documented':270,'reason':'Primary methods describe detector-derived furniture pseudo-labels. Not accepted as expert GT; no independently qualified download/drawing licence here.','license':'Paper licence does not establish dataset drawing rights'},
 {'name':'Campus3D','url':'https://3d.nus.app/','publisher_license':'CC BY-NC-SA4.0','used':False,'reason':'Aerial-derived3Dpointclouds, not site-plan drawing/mask pairs'},
 {'name':'User-supplied venue PDFs','actual_location':str(ROOT/'03_REAL_VENUE_REFERENCES/00_INBOX/PDF_ORIGINALS'),'training_permission':'UNVERIFIED','used':'Read-only four-page PDF decoding/inference and annotation review queue','GT':'None; no positive recognition accuracy or physical stock claim'}
]
save('DATA_SOURCES_AND_LICENSES.json',sources)
packages={}
for name in ['torch','torchvision','ultralytics','segmentation-models-pytorch','numpy','Pillow','opencv-python','shapely','pydantic']:
 try:packages[name]=importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:packages[name]='NOT_FOUND'
save('reports/ENVIRONMENT.json',{'python':sys.version,'executable':sys.executable,'packages':packages,'installed_or_upgraded_packages':[],'global_renderer_python':'C:/Users/User/AppData/Local/Programs/Python/Python312/python.exe','isolation':'Python audit hooks, not complete OS isolation'})
acceptance={'overall':'PARTIAL_DELIVERY_WITH_EXPLICIT_DATA_BLOCKERS','capabilities':[
 {'capability':'Twelve-class existing-object floorplan detection','status':'PARTIAL','demonstrated':'Actual local one-class chair-label pilot and matched synthetic12 baseline','metrics':evaluation,'remaining':'11event classes unvalidated; chair GT incomplete; source-owner/physical venue ancestry unresolved; not production-qualified stock detection'},
 {'capability':'Outdoor true site-boundary recognition','status':'DATA_BLOCKED','eligible_original_raster_training_pairs':0,'trained_model':None,'boundary_iou':None,'positive_recognition_coverage':0,'implemented':'Refuse unqualified raster boundary semantics; do not promote frames or legends','remaining':'Authorized original site drawings with source-supported reviewed boundary targets and document/venue family identity'},
 {'capability':'Outdoor zones/entrances/obstacles/restricted-area recognition','status':'DATA_BLOCKED','trained_model':None,'recognition_metrics':outdoor,'implemented':'Native publisher entrance-label import with exact pixel-cell geometry; NOT raw drawing recognition','remaining':'Original source drawings and reviewed target-specific semantic labels; do not train on colour-coded target labels as if raw sources'}],
 'independent_chair_replay':'objects_v2/INDEPENDENT_METRIC_REPLAY.json','native_conversion_test':'outdoor/CONVERSION_AND_ABSTENTION_TESTS.json','actual_cli':'evidence/CLI_EXECUTION.json','annotation_contract':'annotations/CONTRACT_TESTS_FINAL_V2.json','preservation':'PRESERVATION.json','real_reviews_or_metric_approvals_created':0,'old_models_replaced':False,'browser_review_UI':'JS syntax/local HTTP verified; real browser interaction NOT tested because no CUA browser available','original_A_to_F_eight_logics':'Preserved; S-GCN, weather, planner feedback and detailed safety objectives are not newly implemented or certified'}
save('FUNCTIONAL_ACCEPTANCE.json',acceptance)
# Measured plots only; no invented scientific scores for blocked branches.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
methods=list(evaluation['results']);fig,axs=plt.subplots(1,2,figsize=(10,5))
for ax,key,title in zip(axs,['ap50','ap50_95'],['Chair AP50','Chair AP50-95']):
 vals=[evaluation['results'][m][key] for m in methods];ax.bar(['Synthetic12\nbaseline','Published-chair\npilot'],vals,color=['#777777','#245f83']);ax.set_ylim(0,1);ax.set_ylabel('Published-label AP (0-1)');ax.set_title(title)
 for i,v in enumerate(vals):ax.text(i,v+.02,f'{v:.4f}',ha='center')
fig.suptitle('Matched 86-plan export test; 152 published chair labels; macro denominator 1')
fig.text(.5,.01,'Known incomplete labels and unresolved physical ancestry. Not complete inventory accuracy or all-12-class mAP.',ha='center',fontsize=9);fig.tight_layout(rect=(0,.05,1,.93));fig.savefig(H/'reports/MEASURED_CHAIR_COMPARISON.png',dpi=160);plt.close(fig)
print('Closeout machine evidence and measured chart generated')
