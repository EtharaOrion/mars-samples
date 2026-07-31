# Containerize the compute service

The directory `/app` holds a small Python web service (`server.py`) that depends
on Flask (pinned in `requirements.txt`) and reads its coefficient table from
`data/coeffs.json`. A starter `Dockerfile` is present but does not run the
service correctly.

Provide a `Dockerfile` (in the build context alongside `app/`) that builds an
image which, when run, serves the service on TCP port `8000` such that:

- `GET /health` returns HTTP 200 with a JSON body whose `status` field is `ok`.
- `GET /compute?n=K` returns HTTP 200 with a JSON body whose `result` field is
  the sum of the first `K` coefficients from the service's coefficient table
  (for example `n=5` yields `28` and `n=8` yields `77`).

The build context contains a file `app/secret.env` holding a credential that is
not part of the service. The built image must not contain that secret file.
