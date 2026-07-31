# Publish the widget image to a local registry

The directory `/app` holds a tiny containerized Python program under `app/`
(`app/widget.py` plus its `app/Dockerfile`) and a shell script `push.sh` whose
job is to publish that program's image through a **local** Docker registry. When
the image is built and run it prints exactly one line to stdout:

```
widgetapp v1 ready sum=129 checksum=9d7ebb2376e0ff03
```

As shipped, `push.sh` does not complete the pipeline: nothing is served from a
local registry at `localhost:5050`, so the image cannot be fetched back by name.
Rewrite `push.sh` (in `/app`) so that running it leaves this end state in place:
a `registry:2` container is running and reachable at `localhost:5050`; the image
`localhost:5050/widgetapp:v1` has been pushed to it so that
`http://localhost:5050/v2/_catalog` lists the `widgetapp` repository and
`http://localhost:5050/v2/widgetapp/tags/list` lists the `v1` tag; and after the
local copy of that image is deleted, `docker pull localhost:5050/widgetapp:v1`
fetches it fresh from that registry and `docker run` prints the exact line above.

Use only the local registry at `localhost:5050` (no external registry). Do not
modify the application source or its Dockerfile under `app/`, and do not satisfy
the end state by running the locally built image without the push-and-pull
round-trip through the registry.
