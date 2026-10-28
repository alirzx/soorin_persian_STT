"""Small deterministic HTTP backend for Caddy -> Studio Nginx -> API CI smoke tests.

The production inference image is intentionally not started in this test.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health/ready":
            data = {"ready": True, "model": "ci-mock", "error": None}
        elif self.path == "/v1/models/current":
            data = {"ready": True, "name": "ci-mock", "streaming_mode": "buffered"}
        else:
            self.send_error(404)
            return
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("STT CI mock API listening on 0.0.0.0:8080", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
