# Make the stateful app survive a container recreate

The directory holds a single-service stack defined in `docker-compose.yml`: a
small Python HTTP service `app`, built from `app/`, that keeps its state in the
directory `/data` inside the container (the state lives in `/data/state.json`).
The published host port comes from the `API_HOST_PORT` variable (default 8080)
and is mapped to container port 8080. The service exposes three endpoints, all
returning JSON: `GET /health` returns `{"status":"ok"}`; `GET /put?value=<v>`
records `<v>` and returns `{"stored":"<v>","writes":<n>}` where `<n>` is the
running write count; `GET /get` returns `{"value":<v-or-null>,"writes":<n>}`
reflecting the last recorded value.

The stack currently comes up and serves requests, but the app's `/data`
directory is not durably persisted, so any recorded state is silently lost when
the containers are recreated. Repair the compose configuration so the app's data
directory is backed by durable storage that survives a full recreate — a named
volume mounted at the app's data path. The graded end-state is temporal: after
`docker compose up -d`, recording a value with `GET /put?value=<v>`, then running
`docker compose down` WITHOUT removing volumes and `docker compose up -d` again,
a subsequent `GET /get` MUST return that same `<v>` with its `writes` count
preserved. Change only the compose wiring; do not modify the application source
or the app image build.
