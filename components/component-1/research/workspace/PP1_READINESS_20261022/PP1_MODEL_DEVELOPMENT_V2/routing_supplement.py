"""Actual cropped hybrid execution on known procedural source; geometry stays provisional."""
import platform
from common import *
platform.uname();events=guard()
import torch
torch.set_num_threads(4)
from PIL import Image
from adapter import AnalyzeRequest,analyze
from shapely.geometry import shape,box
p=sorted((H/"yolo/dataset/test/images").glob("*HYBRID*"))[0]
with Image.open(p) as im:w,h=im.size
# Explicit laboratory crop control; not asserted to be a semantically reviewed indoor zone.
region=[20,30,w-20,h-30]
req=AnalyzeRequest(image_path=str(p),venue_type="hybrid",input_kind="floorplan_raster",source_domain="controlled_synthetic",indoor_regions=[region])
r=analyze(req,H/"adapter_outputs/HYBRID_LAB_CROP")
checks=[]
def check(n,v):checks.append({"name":n,"passed":bool(v)})
check("actual cropped U-Net and whole-source YOLO called",r["actual_model_calls"]=={"unet":1,"yolo":1})
geoms=[shape(o["geometry"]) for o in r["candidate_bundle"]["objects"] if o["model"]=="U-Net ResNet18"]
check("crop geometry maps into requested source-pixel region",all(box(*region).buffer(1e-6).covers(g) for g in geoms))
check("no hybrid transitions or metric truth inferred",not r["metric_twin_ready"] and "transitions" in r["unknown"] and r["candidate_bundle"]["boundary"] is None)
check("crop extraction has positive support",bool(geoms) and all(c["polygon_valid"] and c["absolute_area_error"]<1e-6 for c in r["extraction_checks"]))
save("adapter_outputs/HYBRID_CROP_TEST.json",{"status":"PASS" if all(c["passed"] for c in checks) else "FAIL","checks":checks,"source":str(p),"region":region,"scope":"Coordinate/routing controlled test only. The crop is an explicit arbitrary laboratory window, NOT a semantically reviewed indoor zone or new training annotation.","indoor_outdoor_relationship_understanding_validated":False})
save("adapter_outputs/HYBRID_GUARD.json",events)
if not all(c["passed"] for c in checks):raise SystemExit(1)
print("Hybrid routing/coordinate test PASS; semantic indoor/outdoor qualification remains unverified")
