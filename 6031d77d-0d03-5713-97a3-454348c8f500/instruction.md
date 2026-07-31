# Fix the compose stack startup ordering

The workspace holds a small two-service Docker Compose stack. The `app` service
(build context `./app`) needs several seconds to initialize before it begins
serving HTTP on port `8000`; a request to `http://app:8000/` then returns a JSON
body of the form `{"status": "ok", "token": "<value>"}`. The `checker` service
(build context `./checker`, byte-frozen) makes exactly one HTTP call to the app
the moment it starts, and records the outcome of that single attempt to the file
`/out/checker_marker.json` (a bind-mounted directory).

As shipped, `docker compose up` brings the stack "up" but the checker runs before
the app is ready, so it records a failed first call. Edit **only**
`docker-compose.yml` so that, after `docker compose up -d`, the end state is:

- the `app` service reports Docker health status `healthy`; and
- `/out/checker_marker.json` contains exactly
  `{"attempts": 1, "first_attempt_ok": true, "token": "<the value the app serves>"}`,
  i.e. the checker's single first attempt succeeded and read the app's token.

You may change the compose file only. Do not modify the `app` or `checker`
sources, and do not make the checker sleep or retry.
