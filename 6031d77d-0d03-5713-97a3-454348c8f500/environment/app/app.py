import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = "GOLD-star29-a1b2c3"
INIT_DELAY_SEC = 6


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok", "token": TOKEN}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


def main():
    time.sleep(INIT_DELAY_SEC)
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()


main()
