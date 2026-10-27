"""Local dummy-data origin. Never logs headers or submitted payloads."""

import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(20 * 16384))
            self.end_headers()
            try:
                for _ in range(20):
                    self.wfile.write(b"x" * 16384)
                    self.wfile.flush()
                    time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        content = (
            Path(__file__).resolve().parents[1] / "pii-form" / "index.html"
        ).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 256000:
            self.send_error(413)
            return
        self.rfile.read(length)
        body = b"Dummy request reached the local origin: SentriFlow allowed it."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("Dummy origin: http://127.0.0.1:9090; slow download: /stream", flush=True)
    try:
        ThreadingHTTPServer(("127.0.0.1", 9090), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
