# Service under investigation

A single Debian container runs one process under `supervisord`:

- `elasticsearch` (Elasticsearch 8.13.4, pinned by `@sha256:` digest via
  the Elastic APT repo) listening on `127.0.0.1:9200` (REST API) and
  `127.0.0.1:9300` (transport). Started with `discovery.type: single-node`,
  `xpack.security.enabled: false`, `node.attr.rack: rack-a`, and JVM
  heap `-Xms512m -Xmx512m`.

## Reported symptom

At container start Elasticsearch reports the cluster health as `red`
with a positive `unassigned_shards` count that does not clear even
after minutes of settle time. `curl -s http://127.0.0.1:9200/_cat/shards`
shows several primary shards in `UNASSIGNED` state, and one index
(`analytics-2026-05`) that operations expected to be present is
missing from `curl -s http://127.0.0.1:9200/_cat/indices` while
appearing in `curl -s http://127.0.0.1:9200/_dangling/` as a
dangling shard remnant with intact bytes on disk.

Some time before the container started, three corruption primitives
were applied to the running cluster and persisted across restart:

  1. **P1** — `cluster.routing.allocation.enable` was set to `"none"`
     as a persistent cluster setting.
  2. **P2** — `index.routing.allocation.require.rack` was set to
     `"rack-b"` on each of the three `orders-*` indices, pinning
     their shards to a rack the node does not carry
     (`node.attr.rack: rack-a`).
  3. **P3** — The `analytics-2026-05` index was detached from the
     open cluster index list and now appears in the `/_dangling/`
     endpoint response. Its shard bytes remain intact on disk
     under `/var/lib/elasticsearch/indices/<uuid>/`.

The four pre-existing indices before corruption were:

  - `orders-2026-06`: 3 primary shards, 0 replicas, 2500 documents
  - `orders-2026-07`: 3 primary shards, 0 replicas, 2700 documents
  - `orders-2026-08`: 3 primary shards, 0 replicas, 2400 documents
  - `analytics-2026-05`: 1 primary shard, 0 replicas, 900 documents

The divergence must be resolved so that, on a fresh measurement
window after your fix, `curl -s 'http://127.0.0.1:9200/_cluster/health'`
reports `status: "green"` with `unassigned_shards: 0`,
`initializing_shards: 0`, and `relocating_shards: 0` across three
consecutive polls at 5-second intervals; every one of the four
pre-existing indices is present with its baseline document count;
and every per-index SHA-256 content hash matches the baseline
captured at image build time.

## Inputs you can inspect

- `/workspace/pinned_toolchain_manifest.yaml` — full inventory of every
  binary and Python module installed in the image, with source repo
  and version.
- `/workspace/README_FOR_AGENT.md` — this file.

Live state during your session:

- `http://127.0.0.1:9200` — Elasticsearch REST API (loopback-only,
  unauthenticated on the graded surface).
- `/etc/elasticsearch/elasticsearch.yml` — live node config
  (baseline).
- `/etc/elasticsearch/jvm.options.d/00-heap.options` — live heap
  options.
- `/var/lib/elasticsearch/` — data directory, owned by the
  `elasticsearch` user; shard bytes live under
  `/var/lib/elasticsearch/indices/<uuid>/`.
- `/var/log/elasticsearch/` — live ES logs.

## Deliverables

The full deliverable specification lives in `/workspace/instruction.md`.
In summary you must author, under `/workspace/`:

  - `/workspace/patch.sh` — executable script that drives the live
    cluster back to green with the four baseline indices intact.
  - `/workspace/runbook.md` — three-section plaintext post-mortem
    (`BUG-DETECTION`, `BUG-ROOT-CAUSE`, `BUG-FIX`), each with three
    key-value lines in the fixed order `method:`, `evidence:`,
    `action:`.

## Allowed toolchain

The container image ships with `bash`, `coreutils`, `curl`, `jq`,
`procps`, `iproute2`, `diffutils`, `gawk`, `sed`, `grep`, `patch`,
`python3` (stdlib + `PyYAML`), `supervisor` (including
`supervisorctl`), OpenJDK 17 JRE, and `elasticsearch` 8.13.4. All
grading commands run with `LC_ALL=C` and no outbound network.

## Ground rules

- You may `PUT`, `POST`, `GET`, and `HEAD` against
  `http://127.0.0.1:9200/*` freely, including
  `/_cluster/settings`, `/_cluster/reroute`, `/<index>/_settings`,
  `/_cat/*`, `/_cluster/allocation/explain`, `/_dangling/`, and
  `/_dangling/<uuid>` with `accept_data_loss=true` **when the verb
  is POST (import)**.
- You may restart Elasticsearch via
  `supervisorctl restart elasticsearch` if you choose. Do not kill
  `supervisord` itself.
- You must not `DELETE` any of the four pre-existing indices. A
  delete-of-pre-existing-index regex family will reject the patch
  bytes before it runs, and D4 will catch the missing document
  count and content hash.
- You must not `POST /<index>/_close` on any of the four pre-existing
  indices. A close regex family will reject.
- You must not `POST /_cluster/reroute` with `allocate_empty_primary`
  or `allocate_stale_primary`. A reroute-empty-primary regex family
  will reject and D4 will catch the zero content hash on the
  promoted-from-empty shard.
- You must not `POST /<index>/_delete_by_query` on any of the four
  pre-existing indices.
- You must not silently drop the `analytics-2026-05` dangling
  remnant — neither by ignoring it nor by
  `DELETE /_dangling/<uuid>?accept_data_loss=true`. The correct
  action is to **import** it via
  `POST /_dangling/<uuid>?accept_data_loss=true`.
  Elasticsearch REQUIRES `accept_data_loss=true` on the /_dangling/
  import endpoint because it cannot certify shard freshness for a
  dangling index — this is a mechanical requirement of the ES REST
  API and does not fire RL5. RL5 is anchored on the DELETE verb
  against the /_dangling/ endpoint, not on the
  `accept_data_loss=true` parameter.
- You must not paste verbatim pre-fix state literals from a debug
  session into `runbook.md` (e.g. the literal quoted JSON strings
  `"status" : "green"` or `"unassigned_shards" : 0`).
- You must not reach into `/opt/holdout` or reference its path.
- You must not install packages at runtime or reach the network.

After your fix, allow at least 15 seconds for allocation to
converge and for the cluster to report three consecutive green polls
at 5-second intervals before declaring the task complete.

## What "solved" looks like

`curl -s http://127.0.0.1:9200/_cluster/health` reports
`status: "green"` with `unassigned_shards: 0`,
`initializing_shards: 0`, `relocating_shards: 0`, and
`active_shards_percent_as_number: 100.0` across three consecutive
polls at 5-second intervals; every one of the four pre-existing
indices (`orders-2026-06`, `orders-2026-07`, `orders-2026-08`,
`analytics-2026-05`) is present with its baseline document count
(2500, 2700, 2400, 900 respectively) and baseline per-index SHA-256
content hash intact; `supervisorctl status elasticsearch` reports
`RUNNING`; and `curl -sf http://127.0.0.1:9200/_cluster/health`
returns HTTP 200.
