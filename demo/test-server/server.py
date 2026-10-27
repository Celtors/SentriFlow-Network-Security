"""Offline receiver. Discards dummy payloads and never logs request contents."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        page = Path(__file__).resolve().parents[1] / "pii-form" / "index.html"
        body = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 <= size <= 1_048_576:
            self.send_error(413)
            return
        self.rfile.read(size)
        body = b"Dummy request reached the local receiver. No payload was retained.\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # BaseHTTPRequestHandler would include the raw request path in its log.
        return


if __name__ == "__main__":
    print("Dummy receiver: http://127.0.0.1:9090 (payloads are discarded)")
    try:
        ThreadingHTTPServer(("127.0.0.1", 9090), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
