#!/usr/bin/env python3
# Minimal Flask webapp for inv-30. Reads config.py at startup only;
# config changes require supervisorctl restart webapp to take effect.
from __future__ import annotations
import sys
from flask import Flask, jsonify
import psycopg2

sys.path.insert(0, "/etc/webapp")
import config  # noqa: E402

app = Flask(__name__)


def _connect():
    return psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        dbname=config.POSTGRES_DB,
        connect_timeout=3,
    )


@app.route("/health")
def health():
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return jsonify({"db": "ok", "status": "healthy"}), 200
    except psycopg2.OperationalError as e:
        msg = str(e)
        if "password authentication failed" in msg:
            print(f"stale_credential: {msg}", file=sys.stderr, flush=True)
            return jsonify({"db": "stale_credential", "status": "unhealthy"}), 500
        return jsonify({"db": "error", "status": "unhealthy"}), 500


@app.route("/status")
def status():
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT customer_id, email, display_name FROM customer_records LIMIT 3"
            )
            rows = [{"customer_id": r[0], "email": r[1], "display_name": r[2]} for r in cur.fetchall()]
        return jsonify({"rows": rows, "status": "ok"}), 200
    except psycopg2.OperationalError:
        return jsonify({"rows": [], "status": "unhealthy"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
