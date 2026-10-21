"""Qualify actually present SCUT assets. No training from target-mask-as-drawing."""
from common import *
from PIL import Image,ImageDraw
import numpy as np,collections
from outdoor_evidence import polygons
events=guard();base=ROOT/'01_DATASET_DOWNLOADS/09_SCUT_AUTOALP_OFFICIAL/EXTRACTED/SCUT-AutoALP/B.schools'
rows=[];summary=collections.Counter();folder=H/'outdoor';folder.mkdir(exist_ok=True)
legend=H/'acquisition/metadata2/SCUT_Fig2.jpg'
for layout in sorted((base/'layout').glob('*.png'),key=lambda p:int(p.stem)):
 b=base/'boundary'/layout.name
 with Image.open(layout) as im:a=np.array(im.convert('RGB'));size=list(im.size)
 with Image.open(b) as im:ba=np.array(im.convert('RGB'));assert list(im.size)==size
 yellow=(a==[255,255,0]).all(2);site=(ba==[0,0,0]).all(2)
 gs=polygons(yellow);summary['yellow_entrance_pixels']+=int(yellow.sum());summary['entrance_components']+=len(gs)
 rows.append({'id':'SCUT_SCHOOL_'+layout.stem,'layout':str(layout),'layout_sha256':sha(layout),'boundary_annotation':str(b),'boundary_sha256':sha(b),'size_wh':size,
  'legend_sha256':sha(legend),'declared_source_family':'school_'+layout.stem,'physical_campus_identity':'UNKNOWN','original_drawing':None,
  'native_entrance_pixels':int(yellow.sum()),'native_entrance_components':len(gs),'site_range_pixels':int(site.sum()),'rights':'PUBLISHER_ACADEMIC_RESEARCH_ONLY_DRAWING_OWNERSHIP_NOT_TRANSFERRED','eligible_training_original_plan_pair':False})
save('outdoor/SOURCE_REGISTRY.json',rows)
save('outdoor/QUALIFICATION.json',{'records':len(rows),'paired_layout_boundary':len(rows),'original_campus_drawings_present':0,'eligible_raster_model_training_pairs':0,'summary':dict(summary),
 'decision':'DATA_BLOCKED_FOR_REAL_SITE_DRAWING_TRAINING','why':'Campus layout files are simplified semantic target images, not original site drawings. Learning their explicit label colours would not establish recognition of real site plans.',
 'implemented_scope':'Native published entrance annotation ingestion + explicit refusal on unregistered drawings. Boundary/other event semantics not inferred.',
 'license_source':'https://github.com/designfuturelab702/SCUT-AutoALP-Database-Release','legend_source':'figure/Fig2.jpg','site_range_is_not':'legal property boundary or verified event usable region',
 'independence':'IDs are publisher sample identifiers; physical-campus/source-document ancestry unavailable. No held-out learned accuracy claim.', 'guard':events})
print(len(rows),'native annotation pairs;',0,'eligible original-site-drawing training pairs')
