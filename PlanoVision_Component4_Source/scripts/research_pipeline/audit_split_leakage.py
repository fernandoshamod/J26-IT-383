"""Read-only machine-readable leakage audit. Inputs contain metadata, never financial features."""
import argparse
import json
from pathlib import Path
import sys
from component4.dataset_design import audit_split_leakage


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata', required=True, help='JSON array of scenario/family/planning/source metadata')
    p.add_argument('--assignments', required=True, help='JSON object mapping scenario IDs to train/validation/test')
    p.add_argument('--protocol', required=True, choices=['conditional_in_simulator', 'unseen_templates'])
    args = p.parse_args()
    try:
        rows = json.loads(Path(args.metadata).read_text(encoding='utf-8-sig'))
        splits = json.loads(Path(args.assignments).read_text(encoding='utf-8-sig'))
        result = audit_split_leakage(rows, splits, args.protocol)
    except (ValueError, TypeError, OSError) as exc:
        result = {'status': 'FAIL', 'error': str(exc), 'actual_financial_validation': False}
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
