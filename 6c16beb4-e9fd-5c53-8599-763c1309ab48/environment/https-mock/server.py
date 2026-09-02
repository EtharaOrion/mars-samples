import http.server
import ssl
from pathlib import Path

RESPONSES_DIR = Path("/srv/https-mock/responses")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        rel = self.path.lstrip("/")
        target = (RESPONSES_DIR / rel).resolve()
        if not str(target).startswith(str(RESPONSES_DIR.resolve())):
            self._send(403, b"forbidden\n")
            return
        if not target.is_file():
            self._send(404, b"not found\n")
            return
        self._send(200, target.read_bytes())

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def finish(self) -> None:
        try:
            self.wfile.flush()
        except (OSError, ValueError):
            pass
        sock = getattr(self, "connection", None)
        if isinstance(sock, ssl.SSLSocket):
            try:
                sock.unwrap()
            except (OSError, ssl.SSLError, ValueError):
                pass
        super().finish()

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    server = http.server.HTTPServer(("127.0.0.1", 8443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(
        certfile="/srv/https-mock/certs/cert.pem",
        keyfile="/srv/https-mock/certs/key.pem",
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
