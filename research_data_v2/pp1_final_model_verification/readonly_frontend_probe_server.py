"""Temporary read-only evidence server for the existing compiled frontend."""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
sys.dont_write_bytecode = True

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def forward(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))) if self.command == "POST" else None
        request = Request("http://127.0.0.1:8000" + self.path,
                          data=body, method=self.command,
                          headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        try:
            response = urlopen(request, timeout=90)
        except HTTPError as error:
            response = error
        content = response.read()
        self.send_response(response.status)
        self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path.startswith("/api/") or self.path == "/health":
            self.forward()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.forward()
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass

ThreadingHTTPServer(("127.0.0.1", 5173), Handler).serve_forever()

