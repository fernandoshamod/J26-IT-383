"""Executable research entry point; never opens the historical database."""
import argparse
from pathlib import Path
from support import PACKAGE,read,save
def main():
    ap=argparse.ArgumentParser();commands=ap.add_subparsers(dest='command',required=True)
    server=commands.add_parser('serve');server.add_argument('--db',required=True);server.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1']);server.add_argument('--port',type=int,default=8765)
    model=commands.add_parser('understand');model.add_argument('--image',required=True);model.add_argument('--out',required=True)
    schema=commands.add_parser('export-contracts');schema.add_argument('--out',required=True)
    demo=commands.add_parser('demo');demo.add_argument('--out',required=True)
    commands.add_parser('verify-freeze')
    args=ap.parse_args()
    from release import verify_freeze
    freeze=verify_freeze()
    if args.command=='verify-freeze':
        print(freeze);return
    if args.command=='serve':
        import uvicorn
        from api import create_app
        uvicorn.run(create_app(args.db),host=args.host,port=args.port,log_level='warning')
    elif args.command=='understand':
        from understanding import understand
        bundle=understand(args.image,args.out);print('Actual source-bound candidates:',len(bundle['objects']),'Review/calibration gate: BLOCKED. No synthetic substitution.')
    elif args.command=='demo':
        from demo import run_demo
        run_demo(args.out)
    else:
        from contracts import TwinReview,Optimize,Approve
        save(args.out,{'reviewed_twin':TwinReview.model_json_schema(),'optimization':Optimize.model_json_schema(),'reference_approval':Approve.model_json_schema()})
if __name__=='__main__':main()
