"""Correction for touching/diagonal contour rings: exact union of raster cells.
No smoothing/buffer repair, no change to predictions. Pixel support is preserved.
"""
from common import *
import numpy as np,cv2,torch
from PIL import Image
from shapely.geometry import box,mapping
from shapely.ops import unary_union
from shapely.affinity import scale
from prediction_bridge import require_optimizer_ready
def exact_components(accepted,width,height):
    names=['room_region','wall','door','window'];objects=[];checks=[];sx,sy=width/accepted.shape[1],height/accepted.shape[0]
    for cid,label in enumerate(names,1):
        count,labels,stats,_=cv2.connectedComponentsWithStats((accepted==cid).astype(np.uint8),8)
        for k in range(1,count):
            pixels=int(stats[k,cv2.CC_STAT_AREA])
            if pixels<12:continue
            cells=[]
            for y in range(accepted.shape[0]):
                row=labels[y]==k;delta=np.diff(np.r_[False,row,False].astype(np.int8));starts=np.where(delta==1)[0];ends=np.where(delta==-1)[0]
                cells.extend(box(int(a),y,int(b),y+1) for a,b in zip(starts,ends))
            geom=scale(unary_union(cells),xfact=sx,yfact=sy,origin=(0,0));assert geom.is_valid and not geom.is_empty
            expected=pixels*sx*sy;area_error=abs(geom.area-expected);assert area_error<1e-6
            parts=[geom] if geom.geom_type=='Polygon' else list(geom.geoms);coordinates=[mapping(p)['coordinates'] for p in parts];oid=f'UNET_{label}_{k:04d}'
            objects.append(dict(id=oid,semantic_class=label,model='U-Net ResNet18',status='uncertain',source_kind='actual_model_prediction',geometry=dict(type='MultiPolygon',coordinates=coordinates,unit='original_image_pixels',holes_preserved=True,extraction='exact_union_of_thresholded_raster_pixel_cells'),planner_confirmed=False,relocation_allowed=False))
            checks.append(dict(id=oid,predicted_component_pixels=pixels,polygon_count=len(parts),holes=sum(len(p.interiors) for p in parts),polygon_valid=geom.is_valid,area_original_pixels2=geom.area,expected_area_original_pixels2=expected,absolute_area_error=area_error))
    return objects,checks
def main():
    out=HERE/'bridge_v3';out.mkdir(exist_ok=True);prior=read(HERE/'bridge/ACTUAL_IMAGE_SPACE_TWIN.json');d14=read(HERE/'provisional/D14_FRESH/D14_AI_PREDICTIONS_IMAGE_SPACE.json');image_path=Path(d14['source_image']);m=module(ROOT/'PP1_STAGE_E_EVENT_LAYOUT_V2/backend/venue_unet_inference_v2.py','bridge_v3_model');cp=ROOT/'02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt';net=m.load_model(cp,torch.device('cuda'));original=m.load_image(image_path);w,h=original.size
    x=np.array(original.resize((512,512),Image.Resampling.BILINEAR),np.float32)/255;x=(x-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
    with torch.inference_mode():prob=net(torch.from_numpy(x.transpose(2,0,1).copy()).unsqueeze(0).cuda()).softmax(1)[0].cpu().numpy()
    accepted=np.where(prob.max(0)>=.7,prob.argmax(0)+1,0).astype(np.uint8);objects,checks=exact_components(accepted,w,h);old=read(HERE/'bridge/GEOMETRY_CANDIDATE_CHECKS.json');current={c['id']:c['predicted_component_pixels'] for c in checks};previous={c['id']:c['component_pixels'] for c in old}
    assert all(current.get(k)==v for k,v in previous.items()),(previous,current)
    new={**prior,'schema':'IMAGE_SPACE_TWIN_CANDIDATE_V2','objects':objects+[o for o in prior['objects'] if o['model']=='YOLOv8n'],'extraction_version':'RASTER_CELL_UNION_V3'};save(out/'ACTUAL_IMAGE_SPACE_TWIN_V3.json',new);save(out/'EXTRACTION_BEFORE_AFTER.json',dict(before_invalid_polygons=sum(c['invalid_polygon_count'] for c in old),after_invalid_polygons=0,components=len(checks),same_previous_component_pixel_counts=True,additional_previously_discarded_degenerate_contour_components=sorted(set(current)-set(previous)),checks=checks,limitation='Exact representation of thresholded predictions, not proof of real structural accuracy or usable venue boundary'));save(out/'OPTIMIZER_TRANSITION_BLOCKED.json',require_optimizer_ready(new));Image.fromarray(accepted).save(out/'ACCEPTED_MODEL_LABELS.png')
    # Independent metamorphic fixture includes a hole and diagonal contact.
    sample=np.zeros((9,9),np.uint8);sample[1:6,1:6]=2;sample[2:5,2:5]=0;sample[6:8,6:8]=2
    objs,cs=exact_components(sample,9,9);assert all(c['polygon_valid'] for c in cs) and abs(sum(c['area_original_pixels2'] for c in cs)-np.count_nonzero(sample))<1e-9
    save(out/'EXTRACTION_METAMORPHIC_TEST.json',dict(diagonal_and_hole_preserved=True,input_labeled_pixels=int(np.count_nonzero(sample)),component_count=len(cs),checks=cs));print('V3 exact pixel geometry:',len(checks),'valid components; optimizer remains blocked',flush=True)
if __name__=='__main__':main()
