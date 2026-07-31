# Slim down the analytics service image

The build context holds a small Go web service under `app/` (`main.go`, `go.mod`)
that reads its coefficient table from `app/data/table.txt` at runtime. The shipped
`Dockerfile` builds and runs the service, but it is built with a single stage that
keeps the entire Go toolchain in the final image, producing a needlessly large
artifact.

Author a `Dockerfile` (in the build context alongside `app/`) that produces a much
smaller runnable image while preserving behaviour. When the image is run it must
serve the service on TCP port `8000` such that:

- `GET /health` returns HTTP 200 with a JSON body whose `status` field is `ok`.
- `GET /compute?n=K` returns HTTP 200 with a JSON body whose `result` field is the
  sum of the first `K` entries of the service's coefficient table (for example
  `n=5` yields `26` and `n=8` yields `39`).

The final image must be smaller than `100 MB` (100000000 bytes as reported by
`docker image inspect -f '{{.Size}}'`). You may only edit the `Dockerfile`; the Go
sources and the data file under `app/` must remain byte-for-byte unchanged.
