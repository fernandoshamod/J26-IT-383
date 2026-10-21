"""Run a single user-planned package calculation, without creating event rows."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from component4.public_package_benchmark import load_evidence, estimate_package

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', default='config/public_hotel_benchmark.v0.1.json')
parser.add_argument('--evidence-id', required=True)
parser.add_argument('--guests', required=True, type=int)
parser.add_argument('--event-type', required=True, choices=['Wedding', 'Corporate'])
parser.add_argument('--event-date', help='ISO date; optional. Does not confirm hotel availability.')
args = parser.parse_args()
try:
    config, evidence = load_evidence(args.config)
    result = estimate_package(evidence, args.evidence_id, args.guests, args.event_type, args.event_date)
    result['config_version'] = config['config_version']
    result['source_snapshot_sha256'] = config['evidence_sha256']
    print(json.dumps(result, indent=2, allow_nan=False))
except (ValueError, KeyError) as exc:
    parser.exit(2, f'Cannot calculate: {exc}\n')
