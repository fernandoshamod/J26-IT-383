"""Build a new versioned observational package; no synthetic execution or training."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.historical_refinement import build, write_new_package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--destination', required=True, help='New directory within data/refined')
    parser.add_argument('--node')
    parser.add_argument('--exporter')
    parser.add_argument('--workbook-source', help='Recover an already saved XLSX only after full cell verification')
    parser.add_argument('--source-renderer-returncode', type=int)
    args = parser.parse_args()
    parent = (ROOT / 'data/refined').resolve()
    destination = (ROOT / args.destination).resolve()
    if destination == parent or not destination.is_relative_to(parent):
        raise ValueError('Destination must be a new version below data/refined')
    bundle = build(ROOT, args.as_of)
    parent.mkdir(exist_ok=True)
    stats = write_new_package(bundle, destination, ROOT, args.node, args.exporter,
                              args.workbook_source, args.source_renderer_returncode)
    print(json.dumps({k: v for k, v in stats.items() if k not in
                     {'source_hashes', 'publisher_hashes', 'code_hashes', 'files'}}, indent=2))


if __name__ == '__main__':
    main()
