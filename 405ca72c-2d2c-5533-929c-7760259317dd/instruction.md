# Launch the compute service under a strict hardening policy

The build context under `environment/` contains a small Python compute service
(`app/server.py`, stdlib only) and a `Dockerfile` that builds an image running
the service on TCP port `8000`. The service exposes `GET /health` (returns
`{"status":"ok"}`) and `GET /compute` (returns a JSON body whose `status` is
`"ok"`, `service` is `"star30"`, and `result` is `77`). The image as shipped is
launched insecurely (as root, with a writable root filesystem and the default
Linux capability set).

Produce a run specification named `run.sh` (a shell script that performs a
single `docker run -d --name "$NAME" ... "$IMAGE"`, reading the image tag from
the environment variable `IMAGE` and the container name from `NAME`) that starts
the container so that ALL of the following hold at the same time while the
service still returns its golden `/compute` response:

- the container process runs as a **non-root** user (effective UID is not `0`);
- the root filesystem is **read-only** (`--read-only`), with a writable mount
  provided ONLY at the single path the service genuinely needs to write;
- **all Linux capabilities are dropped** (`--cap-drop ALL`), adding back at most
  one capability and only if strictly required;
- privilege escalation is disabled via `--security-opt no-new-privileges`.

You may only author the run specification / security configuration. Do not edit
the service source or the build inputs to make the service easier to run.
