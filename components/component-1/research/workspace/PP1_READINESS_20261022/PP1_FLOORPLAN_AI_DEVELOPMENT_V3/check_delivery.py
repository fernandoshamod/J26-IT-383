"""Final numeric/contract checks and complete new-file register."""
import csv,ast,sys
from common import *
checks=[]
def check(n,v):
 checks.append({"name":n,"passed":bool(v)})
 if not v:raise AssertionError(n)
for f in H.glob("*.py"):ast.parse(f.read_text(encoding="utf-8"))
check("source syntax",True)
ev=read(H/"unet/EVALUATION.json")
for model,domains in ev.items():
 for domain,r in domains.items():
  check(model+domain+" mean denominator4",len(r["pooled_metrics"]["class_iou"])==4 and abs(sum(r["pooled_metrics"]["class_iou"])/4-r["pooled_metrics"]["miou"])<1e-12)
  check(model+domain+" raw matrix support",sum(map(sum,r["pooled_confusion"]))==sum(r["pooled_metrics"]["support"]))
symbols=read(H/"symbols/EVALUATION.json")
check("symbol macro denominator2",symbols["class_indices"]==[0,1] and abs(sum(symbols["ap50"])/2-symbols["metrics"]["metrics/mAP50(B)"])<1e-12)
check("new U-Net checkpoint",sha(read(H/"unet/TRAINING_RESULT.json")["best_checkpoint"])==read(H/"unet/TRAINING_RESULT.json")["sha256"])
check("new symbol checkpoint",sha(read(H/"symbols/TRAINING_RESULT.json")["checkpoint"])==symbols["checkpoint_sha256"])
check("actual CLI success",read(H/"CLI_EXECUTION.json")["exit_code"]==0)
check("actual review CLI refusal",read(H/"REVIEW_CLI_EXECUTION.json")["exit_code"]==2)
check("all upload cases remain unapproved",not read(H/"cli/INDOOR_FINAL/UPLOAD_RESULT.json")["approved"] and all(not r["metric_ready"] for r in read(H/"uploads/TEST_RESULTS.json")["runs"]))
check("preservation final",read(H/"PRESERVATION.json")["status"]=="PASS")
# Numeric schema refusal: explicitly invalid contract probe, NOT an invented venue measurement.
sys.path.insert(0,str(ROOT/"PP1_READINESS_20261022/PP1_EXECUTABLE_V1"))
from contracts import Control
from pydantic import ValidationError
for bad in [0.,-1.,float("nan"),float("inf")]:
 try:Control.model_validate({"point_a_px":[0.,0.],"point_b_px":[1.,0.],"known_distance_m":bad,"evidence_ref":"CONTROLLED_INVALID_CONTRACT_PROBE"});raise AssertionError("invalid scale accepted")
 except ValidationError:check("frozen numeric control rejects "+str(bad),True)
save("FINAL_DELIVERY_CHECKS.json",{"status":"PASS","checks":checks,"scope":"Numerical/provenance/schema/functional checks, not whole model or real-world semantic acceptance."})
save("MODEL_IDENTITIES.json",{"unet":read(H/"unet/TRAINING_RESULT.json"),"native_opening_yolo":read(H/"symbols/TRAINING_RESULT.json"),"preserved_event12_yolo":read(ROOT/"PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/yolo/TRAINING_RESULT.json")})
def purpose(p):
 s=p.relative_to(H).as_posix()
 if s.startswith("acquired/"):return "Explicit downloaded primary source, weight, licensed map or rights metadata"
 if s.startswith("runtime/"):return "Isolated settings/font/cache/temp produced by installed local dependencies"
 if s.startswith("unet/data/"):return "Native raster letterbox training/validation/test export; unknown ignored"
 if s.startswith("symbols/data/"):return "Native opening-symbol training image/label export, separate2classontology"
 if s.startswith("unet/predictions/"):return "Actual source/GT/argmax/overlay evidence for every compared record"
 if s.startswith("symbols/predictions"):return "Actual opening detector raw or conf0.25 prediction visualization"
 if "/weights/" in s or p.suffix==".pt":return "Actual newly trained checkpoint; original model not replaced"
 if s.startswith("uploads/") or s.startswith("cli/"):return "Executed document/model/geometry/pending review/refusal evidence; original document copies remain local"
 if s.startswith("upload_test_fixtures/"):return "Explicit analytic synthetic negative/control fixture, not real venue truth"
 if p.suffix==".py":return "Isolated executable implementation or verification source; acquired source is never imported as training substitute"
 if p.suffix==".md":return "Evidence-based technical results, acceptance, failure disclosure or exact runbook"
 return "Machine provenance/config/history/metric/hash/log/contract artifact"
files=sorted(p for p in H.rglob("*") if p.is_file())
with (H/"FILE_REGISTER.csv").open("x",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["path","purpose","bytes","sha256"]);w.writeheader()
 for p in files:w.writerow({"path":p.relative_to(H).as_posix(),"purpose":purpose(p),"bytes":p.stat().st_size,"sha256":sha(p)})
 # Manifest self entries have no circular hash; DELIVERY_SHA256 covers this register.
 w.writerow({"path":"FILE_REGISTER.csv","purpose":"Complete new file/purpose register; self hash in DELIVERY_SHA256","bytes":"","sha256":""})
 w.writerow({"path":"DELIVERY_SHA256.json","purpose":"Final artifact hashes; excludes itself to avoid circular digest","bytes":"","sha256":""})
save("DELIVERY_SHA256.json",{p.relative_to(H).as_posix():sha(p) for p in H.rglob("*") if p.is_file() and p.name!="DELIVERY_SHA256.json"})
print("Delivery PASS",len(checks),"checks,",len(files)+2,"registered files. No further model execution.")
