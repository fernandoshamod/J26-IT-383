"""Start the local dashboard before opening Chrome; keep server errors visible."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def ready(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/planner/config',timeout=2) as r:
            data=json.load(r)
        with urlopen(f'http://127.0.0.1:{port}/api/planner/model-evidence',timeout=2) as r:
            evidence=json.load(r)
        with urlopen(f'http://127.0.0.1:{port}/',timeout=2) as r:
            page=r.read()
        with urlopen(f'http://127.0.0.1:{port}/api/planner/storage',timeout=2) as r:
            storage=json.load(r)
        return (data.get('version')=='lkr-dashboard.0.1' and data.get('mode')=='research_only'
                and data.get('app_revision')=='planner-extended-scope.20261019'
                and evidence.get('version')=='v3.1-frozen-diagnostics'
                and evidence.get('model_run')==data.get('model_run')
                and page==(ROOT/'frontend/dist/index.html').read_bytes()
                and storage.get('version')=='planner-records.1')
    except (URLError,OSError,ValueError):return False


def open_chrome(url):
    candidates=[Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                Path('C:/Program Files (x86)/Google/Chrome/Application/chrome.exe')]
    if os.environ.get('LOCALAPPDATA'):
        candidates.append(Path(os.environ['LOCALAPPDATA'])/'Google/Chrome/Application/chrome.exe')
    for path in candidates:
        if path.is_file():
            subprocess.Popen([str(path),url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            return 'Google Chrome'
    webbrowser.open(url)
    return 'default browser (Chrome not found in standard locations)'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--smoke-test',action='store_true')
    args=parser.parse_args()
    if not (ROOT/'frontend/dist/index.html').is_file():
        print('Dashboard build missing. See README_FINANCIAL_DASHBOARD.md.',flush=True);return 1
    if not args.smoke_test:
        try:
            from component4.local_llm_runtime import ensure_runtime
            llm=ensure_runtime()
            print('Local AI report model:',llm['model'],'READY' if llm['ready'] else 'not installed; run Setup_Local_AI.cmd',flush=True)
        except (OSError,ValueError,RuntimeError):print('Local AI unavailable. Financial engine still works; run Setup_Local_AI.cmd for local reports.',flush=True)
    url=f'http://127.0.0.1:{args.port}'
    if not args.smoke_test and ready(args.port):
        print('Existing dashboard is ready:',url,flush=True)
        if not args.no_browser:print('Opened in',open_chrome(url),flush=True)
        print('Keep the existing server terminal open.',flush=True);return 0
    print('Starting dashboard. Loading verified models; please wait...',flush=True)
    from component4.planner_dashboard_http import create_server
    try:server=create_server(0 if args.smoke_test else args.port)
    except OSError as exc:
        print('Cannot start local server:',exc,flush=True)
        print('The port may contain an older dashboard or another application. No process was stopped.',flush=True)
        print('Close the old dashboard terminal, then start this copy again. Or use --port 8766.',flush=True);return 1
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}'
    try:
        if not ready(server.server_port):
            print('Readiness check failed. Browser was not opened.',flush=True);return 1
        print('READY:',url,flush=True)
        if args.smoke_test:
            with urlopen(url,timeout=3) as response:
                assert response.status==200 and b'<div id="root">' in response.read()
            print('PASS: backend and built frontend are reachable.',flush=True);return 0
        if not args.no_browser:print('Opened in',open_chrome(url),flush=True)
        print('KEEP THIS WINDOW OPEN while using Chrome. Ctrl+C stops the dashboard.',flush=True)
        while thread.is_alive():thread.join(timeout=1)
    except KeyboardInterrupt:print('\nStopping dashboard...',flush=True)
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    return 0


if __name__=='__main__':raise SystemExit(main())
