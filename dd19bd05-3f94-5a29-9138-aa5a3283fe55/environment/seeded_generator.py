#!/usr/bin/env python3
"""FORGE inv-26 seeded generator.

Creates the four pre-existing indices (orders-2026-06, orders-2026-07,
orders-2026-08, analytics-2026-05) with pinned settings and mappings,
seeds them with a deterministic set of documents, and refreshes them.

Determinism: a fixed 64-hex seed constant (SEED_HEX below) drives an
independent random.Random per index, so per-index document streams are
independent of index creation order. Every JSON payload is serialised
in canonical form: json.dumps(obj, sort_keys=True, separators=(",", ":"),
ensure_ascii=True). Integer ids serialise as canonical decimal without
leading zero. No float fields exist anywhere in the schema.

The SEED_HEX constant is authored to match the pre-canary bundle hash
of the frozen Stage 2 bundle, in the sense described in
solution/grounding.yaml (HMAC-SHA256(pre_canary_hash,
b"seeded-generator-v1")). At authoring time the value is written by
hand and pinned into the bundle bytes; the pre-canary hash is
independent of this pin because the hash is computed over
canary-stripped bytes and this constant is not a canary.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.request

ES_BASE = "http://127.0.0.1:9200"

SEED_HEX = "5f4e3d2c1b0a99887766554433221100ffeeddccbbaa998877665544332211aa"

CANONICAL_TAGS = (
    "alpha", "bravo", "charlie", "delta",
    "echo", "foxtrot", "golf", "hotel",
)

INDICES = (
    {"name": "orders-2026-06", "shards": 3, "replicas": 0, "docs": 2500},
    {"name": "orders-2026-07", "shards": 3, "replicas": 0, "docs": 2700},
    {"name": "orders-2026-08", "shards": 3, "replicas": 0, "docs": 2400},
    {"name": "analytics-2026-05", "shards": 1, "replicas": 0, "docs": 900},
)

INDEX_MAPPING = {
    "properties": {
        "id": {"type": "integer"},
        "index_name": {"type": "keyword"},
        "seq": {"type": "integer"},
        "payload": {"type": "keyword"},
        "tag": {"type": "keyword"},
    }
}


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def http_request(method: str, path: str, body: bytes | None = None,
                 content_type: str = "application/json") -> tuple[int, bytes]:
    req = urllib.request.Request(ES_BASE + path, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def wait_for_ready(max_wait_s: int = 180) -> None:
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        try:
            status, body = http_request("GET", "/_cluster/health?wait_for_status=yellow&timeout=5s")
            if status == 200:
                data = json.loads(body)
                if data.get("status") in ("yellow", "green"):
                    return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit("ES did not become ready within %d s" % max_wait_s)


def index_rng(index_name: str) -> random.Random:
    h = hashlib.sha256((SEED_HEX + ":" + index_name).encode("ascii")).hexdigest()
    return random.Random(int(h[:16], 16))


def payload_for(index_name: str, doc_id: int, rng: random.Random) -> str:
    material = hashlib.sha256(
        (SEED_HEX + ":" + index_name + ":" + str(doc_id)).encode("ascii")
    ).hexdigest()
    burn = rng.random()  # advance rng state deterministically per doc
    return "p" + material[:24]


def make_document(index_name: str, doc_id: int, rng: random.Random) -> dict:
    tag_idx = rng.randrange(len(CANONICAL_TAGS))
    return {
        "id": doc_id,
        "index_name": index_name,
        "seq": doc_id,
        "payload": payload_for(index_name, doc_id, rng),
        "tag": CANONICAL_TAGS[tag_idx],
    }


def create_index(spec: dict) -> None:
    body = canonical_json({
        "settings": {
            "index": {
                "number_of_shards": spec["shards"],
                "number_of_replicas": spec["replicas"],
                "refresh_interval": "1s",
            }
        },
        "mappings": INDEX_MAPPING,
    }).encode("ascii")
    status, resp = http_request("PUT", "/" + spec["name"], body)
    if status not in (200, 201):
        raise SystemExit(
            "index create failed for %s: %d %s" % (spec["name"], status, resp[:400])
        )


def bulk_index(spec: dict) -> None:
    name = spec["name"]
    docs = spec["docs"]
    rng = index_rng(name)
    batch_size = 500
    lines: list[str] = []
    for doc_id in range(1, docs + 1):
        action = canonical_json({"index": {"_index": name, "_id": str(doc_id)}})
        source = canonical_json(make_document(name, doc_id, rng))
        lines.append(action)
        lines.append(source)
        if len(lines) >= batch_size * 2:
            _flush_bulk(lines)
            lines = []
    if lines:
        _flush_bulk(lines)
    status, resp = http_request("POST", "/" + name + "/_refresh")
    if status != 200:
        raise SystemExit(
            "refresh failed for %s: %d %s" % (name, status, resp[:400])
        )


def _flush_bulk(lines: list[str]) -> None:
    body = ("\n".join(lines) + "\n").encode("ascii")
    status, resp = http_request(
        "POST", "/_bulk", body, content_type="application/x-ndjson"
    )
    if status != 200:
        raise SystemExit("bulk failed: %d %s" % (status, resp[:400]))
    data = json.loads(resp)
    if data.get("errors"):
        first_err = None
        for item in data.get("items", []):
            op = next(iter(item.values()))
            if op.get("error"):
                first_err = op.get("error")
                break
        raise SystemExit("bulk had errors, first: " + repr(first_err)[:400])


def verify_count(spec: dict) -> None:
    status, body = http_request("GET", "/" + spec["name"] + "/_count")
    if status != 200:
        raise SystemExit("count failed for %s: %d" % (spec["name"], status))
    data = json.loads(body)
    if data.get("count") != spec["docs"]:
        raise SystemExit(
            "count mismatch on %s: got %d want %d" %
            (spec["name"], data.get("count", -1), spec["docs"])
        )


def main() -> int:
    wait_for_ready()
    # Optional argv[1] filter lets the bootstrap seed orders and analytics in
    # two separate passes so a pre-analytics _state/ snapshot can be captured
    # between them. Per-index RNG is keyed by index name, so splitting the run
    # does not change per-index document content or content hashes.
    filt = sys.argv[1] if len(sys.argv) > 1 else "all"
    if filt == "orders":
        specs = [s for s in INDICES if s["name"].startswith("orders-")]
    elif filt == "analytics":
        specs = [s for s in INDICES if s["name"].startswith("analytics-")]
    elif filt == "all":
        specs = list(INDICES)
    else:
        raise SystemExit("unknown filter: " + filt)
    for spec in specs:
        create_index(spec)
        bulk_index(spec)
        verify_count(spec)
    status, _ = http_request("POST", "/_flush?wait_if_ongoing=true")
    if status != 200:
        raise SystemExit("flush failed: %d" % status)
    print("seeded_generator: %d indices seeded and flushed (filter=%s)" %
          (len(specs), filt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
