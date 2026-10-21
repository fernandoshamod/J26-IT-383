"""One actual CLI smoke test, final schemas/metrics checks and file register."""
import ast,csv,subprocess,time
from common import *
argv=[sys.executable,"-B","PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/infer.py","--request",
 "PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/INDOOR_REQUEST.json","--out",
 "PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/demos/MY_INDOOR_001"]
t=time.perf_counter()
with (H/"CLI.stdout.log").open("x",encoding="utf-8") as out,(H/"CLI.stderr.log").open("x",encoding="utf-8") as err:
 p=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save("CLI_EXECUTION.json",{"argv":argv,"cwd":str(ROOT),"exit_code":p.returncode,"seconds":time.perf_counter()-t,"stdout":"CLI.stdout.log","stderr":"CLI.stderr.log"})
assert p.returncode==0
checks=[]
def check(n,v):
 checks.append({"name":n,"passed":bool(v)})
 if not v:raise AssertionError(n)
for f in H.glob("*.py"):ast.parse(f.read_text(encoding="utf-8"))
check("all current Python sources syntax valid",True)
result=read(H/"demos/MY_INDOOR_001/RESULT.json")
check("CLI actual local models",result["actual_model_calls"]=={"unet":1,"yolo":1})
check("CLI no fabricated metric approval",not result["metric_twin_ready"] and result["candidate_bundle"]["metres_per_pixel"] is None and not result["candidate_bundle"]["optimization_ready"])
selection=read(H/"yolo/MODEL_SELECTION.json");compare=read(H/"yolo/COMPARISON.json")
for label in ["incumbent","candidate"]:
 row=compare["diagnostic_test"][label]
 check(label+" diagnostic class support denominator11",len(row["class_indices"])==11 and 1 not in row["class_indices"])
 check(label+" AP average denominator matches",abs(sum(row["per_class_ap50"])/11-row["metrics"]["metrics/mAP50(B)"])<1e-12)
 check(label+" AP50-95 average denominator matches",abs(sum(row["per_class_ap50_95"])/11-row["metrics"]["metrics/mAP50-95(B)"])<1e-12)
check("selected checkpoint hash exact",sha(selection["selected_checkpoint"])==selection["selected_sha256"])
protected=read(H/"PROTECTED_SOURCE_HASHES.json")
check("originals final rehash",all(sha(ROOT/p)==h for p,h in protected.items()))
check("independent raw detection replay",read(H/"yolo/INDEPENDENT_DETECTION_VERIFICATION.json")["status"]=="PASS")
check("no unsupported U-Net training claim",read(H/"MODEL_ACCEPTANCE.json")["new_unet_trained"] is False and read(H/"unet/READINESS_GATE.json")["status"]=="BLOCKED")
save("FINAL_DELIVERY_TESTS.json",{"status":"PASS","checks":checks,"limits":"Scope/contract/data-preservation checks, not independent real-domain model acceptance."})
def purpose(p):
 name=p.relative_to(H).as_posix()
 if name.startswith("failures/"):return "Preserved failed/interrupted setup or withdrawn fixture evidence"
 if name.startswith("runtime/"):return "Isolated local settings/font/dependency runtime artifacts"
 if "/dataset/" in name:return "Isolated procedural image/label copy; train repetitions recorded"
 if "/weights/" in name:return "Actual locally trained checkpoint"
 if name.startswith("unet/"):return "Unapproved source-family/review candidate evidence; not training approval"
 if name.startswith("adapter_outputs/") or name.startswith("demos/"):return "Actual candidate-only inference, schema, routing and review-negative evidence"
 if name.startswith("yolo/"):return "Training/evaluation/raw prediction/independent metric evidence"
 if p.suffix==".py":return "Executed new isolated source or local inference entrypoint"
 if p.suffix==".md":return "Evidence-based method, acceptance, limitations or reproduction document"
 return "Execution provenance, hashes, schema or QA result"
files=sorted(p for p in H.rglob("*") if p.is_file())
with (H/"FILE_REGISTER.csv").open("x",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["path","purpose","bytes","sha256"]);w.writeheader()
 for p in files:w.writerow({"path":p.relative_to(H).as_posix(),"purpose":purpose(p),"bytes":p.stat().st_size,"sha256":sha(p)})
save("DELIVERY_SHA256.json",{p.relative_to(H).as_posix():sha(p) for p in H.rglob("*") if p.is_file() and p.name!="DELIVERY_SHA256.json"})
print("Final delivery PASS",len(checks),"checks; actual CLI exit0; source preservation PASS")
