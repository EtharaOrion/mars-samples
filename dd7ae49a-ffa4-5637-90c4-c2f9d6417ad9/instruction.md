# Repair the order-lookup compose stack

The directory holds a three-service stack defined in `docker-compose.yml`: a Go
HTTP API (`api`, built from `app/`), a Postgres database (`db`), and a Redis
cache (`redis`). Postgres is seeded at first boot from `app/initdb/seed.sql`.
The API exposes `GET /order/{id}`: it looks the order up in Postgres, writes the
row into Redis, and returns it as JSON. On a later request for the same id it
serves the row straight from Redis. The stack currently starts, but the API
cannot reach its data and `GET /order/42` does not return the seeded order.

Fix only the compose wiring (`docker-compose.yml`) and, if needed, the API build
file `app/Dockerfile`. Do not modify the Go sources under `app/`, the seed file
`app/initdb/seed.sql`, or the test files. After `docker compose up -d --build`,
once all three services are healthy, `GET /order/42` on the API's published port
must return HTTP 200 with the JSON body
`{"id":42,"customer":"Ada Lovelace","amount_cents":189900,"status":"shipped","source":"db"}`
(the `source` field is `db` on the first read and `cache` on the next read of the
same id, and the Redis key `order:42` must exist after a lookup). The published
API port is provided by the `API_HOST_PORT` build/run variable (default 8042).
