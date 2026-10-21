"""Start the local Component 4 dashboard API; Ctrl+C stops it."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from component4.local_dashboard_http import create_server

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8764)
parser.add_argument('--enable-unitless-research', action='store_true', help='Explicitly load saved research models and hypothetical Monte Carlo; never enables LKR live mode')
args = parser.parse_args()
server = create_server(args.port, enable_unitless_research=args.enable_unitless_research)
print(f'Component 4 local API: http://127.0.0.1:{server.server_port}/api/health', flush=True)
print('Public package benchmarks available. Full LKR live calculations remain blocked. No mock fallback.', flush=True)
if args.enable_unitless_research:
    print('UNITLESS RESEARCH endpoints enabled: /api/research/unitless/calculate and /what-if. NOT LKR, calibrated probabilities or health scores.', flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
