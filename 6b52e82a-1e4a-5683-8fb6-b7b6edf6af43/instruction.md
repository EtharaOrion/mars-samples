# Wire the client and server onto one network

The directory `/app` holds a two-service stack defined in `docker-compose.yml`. A
`server` service runs a small HTTP service on TCP port `8000` that answers
`GET /data` with a fixed JSON document. A `client` service starts, repeatedly
tries to fetch `http://server:8000/data`, and — on success — writes the exact
JSON it received to `/out/marker.json` (the `client` bind-mounts the build
context's `./out` directory at `/out`). The client's target host is the literal
name `server`, so it depends entirely on Docker's embedded DNS resolving that
service name to the server container.

As shipped, the stack is misconfigured: the `client` never manages to resolve or
reach `server`, so no marker file is produced. Edit `docker-compose.yml` (only)
so that, when the stack is brought up, the `client` resolves `server` by name
over Docker's embedded DNS and successfully fetches the document, causing
`./out/marker.json` to be written containing the server's JSON body
(the object `{"service": "server", "sum": 385, "token": "2f6063993261e912"}`).
Do not change the client or server application source, and do not make the client
reach the server by a hardcoded IP address or via host networking — the client
must reach `server` by that service name over a user-defined Docker network.
