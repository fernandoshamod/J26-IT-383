"""VS Code development entry point for the existing verified Python API."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535.')
    from component4.planner_dashboard_http import create_server
    try:
        server = create_server(args.port)
    except OSError as exc:
        print(f'Cannot start API: {exc}. Stop the old server or choose another port.', flush=True)
        return 1
    print(f'PlanoVision Python API: http://127.0.0.1:{args.port}', flush=True)
    print(f'SQLite database: {ROOT / "runtime/planner.sqlite3"}', flush=True)
    print('Local development only. Ctrl+C stops this server.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
