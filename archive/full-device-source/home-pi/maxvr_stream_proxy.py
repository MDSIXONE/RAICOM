#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.request
import socket

SOURCE_URL = "http://127.0.0.1:8090/stream.mjpg"
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 5001
TARGET_PATH = "/video_feed"

class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args), flush=True)

    def do_GET(self):
        if self.path.split("?", 1)[0] != TARGET_PATH:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"MAXVR stream proxy: use /video_feed\n")
            return

        try:
            req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "MAXVR-stream-proxy"})
            with urllib.request.urlopen(req, timeout=10) as upstream:
                content_type = upstream.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                while True:
                    chunk = upstream.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            try:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(("MAXVR stream proxy upstream error: %s\n" % exc).encode("utf-8", "replace"))
            except Exception:
                pass

class ReuseServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    socket.setdefaulttimeout(10)
    server = ReuseServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print("MAXVR stream proxy listening on %s:%s -> %s" % (LISTEN_HOST, LISTEN_PORT, SOURCE_URL), flush=True)
    server.serve_forever()
