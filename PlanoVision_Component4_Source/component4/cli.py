"""Read-only calculator/gate inspection. No scenario generation."""
import argparse, json
from pathlib import Path
from .engine import evaluate
from .gates import pilot_blockers

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--event', choices=['Wedding','Corporate'], default='Wedding')
    parser.add_argument('--mock-test-fixture', action='store_true')
    parser.add_argument('--pilot-gates', action='store_true')
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    result={'pilot_authorized':False,'blockers':pilot_blockers(config)} if args.pilot_gates else evaluate(config,args.event,mode='mock_test_fixture' if args.mock_test_fixture else 'live')
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__=='__main__':main()
