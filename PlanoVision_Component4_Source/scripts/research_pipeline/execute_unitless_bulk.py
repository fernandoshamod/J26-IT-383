"""Bulk execution CLI. Separate exact-hash authorization is mandatory."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.unitless_bulk import blockers, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorization', default='config/unitless_bulk_authorization.v0.1.user.json')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--destination', default='data/final/unitless-bulk-v0.1')
    args = parser.parse_args()
    c = json.loads((ROOT / 'config/unitless_bulk_candidate.v0.1.proposed.json').read_text())
    path = ROOT / args.authorization
    a = json.loads(path.read_text()) if path.is_file() else {}
    reasons = blockers(c, a)
    if reasons:
        print(json.dumps({'status': 'BLOCKED', 'reasons': reasons, 'research_rows_generated': 0}, indent=2))
        if args.execute:
            raise SystemExit(2)
        return
    if not args.execute:
        print(json.dumps({'status': 'AUTHORIZED_GATES_PASS', 'execution_requested': False, 'research_rows_generated': 0}))
        return
    env = dict(os.environ, TEMP=str(ROOT / 'work'), TMP=str(ROOT / 'work'))
    suite = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT, env=env)
    if suite.returncode:
        raise SystemExit('Current tests failed; no bulk output written.')
    # Restrict destination to a fresh child of data/final; never overwrite legacy data.
    dest = (ROOT / args.destination).resolve()
    if dest.parent != (ROOT / 'data/final').resolve():
        raise ValueError('new_child_of_data_final_required')
    node = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    result = write(c, a, dest, node, c['master_columns'])
    print(json.dumps({'status': 'GENERATED_PENDING_FINAL_AUDIT', 'path': str(result),
                      'rows': c['sampling']['rows'], 'unit': 'dimensionless_score',
                      'realism_validated': False, 'model_training_performed': False}, indent=2))


if __name__ == '__main__':
    main()
