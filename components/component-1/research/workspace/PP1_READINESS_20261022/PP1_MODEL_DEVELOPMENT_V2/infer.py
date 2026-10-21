"""Local CLI for the versioned candidate-only adapter."""
import argparse,platform
from common import *
platform.uname()
from adapter import AnalyzeRequest,analyze
parser=argparse.ArgumentParser()
parser.add_argument("--request",required=True,type=Path)
parser.add_argument("--out",required=True,type=Path)
args=parser.parse_args()
req=AnalyzeRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
events=guard()
try:
 result=analyze(req,args.out)
 print(result["route"]["status"],result["actual_model_calls"],"optimization_ready=False")
finally:
 if args.out.is_dir():
  with (args.out/"GUARD.json").open("x",encoding="utf-8") as f:json.dump(events,f,indent=2)
