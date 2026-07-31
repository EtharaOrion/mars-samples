import json
from flask import Flask, request, jsonify

app = Flask(__name__)


def load_coeffs():
    try:
        with open("data/coeffs.json") as fh:
            return json.load(fh)
    except Exception:
        return []


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "compute"}), 200


@app.get("/compute")
def compute():
    n = int(request.args.get("n", "0"))
    coeffs = load_coeffs()
    return jsonify({"n": n, "result": sum(coeffs[:n])}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
