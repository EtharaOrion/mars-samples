# Configure rootless container UID mapping

The workspace at `/app` prepares an unprivileged user `appuser` (uid 1000) to run
a container with Podman WITHOUT root. A short workload script `/app/workload.sh`
is the container's command: it prints its own uid, reads the first line of a
bind-mounted file at `/mnt/owned.txt`, and appends one line to it. On the host a
file `/work/owned.txt` is owned by uid 1000 with mode 0600 (only its owner may
read or write it). The rootless configuration under `/app/rootless/` is only
half-set, so the intended invocation either fails to start or the process inside
the container is mapped to the wrong uid and cannot touch the owner-only file.

Fix the rootless configuration so that, run AS the unprivileged `appuser`, the
invocation `/app/rootless/run.sh` launches the container successfully and the
container process is mapped to uid `1000`: inside the container `id -u` MUST print
`1000`, and the workload MUST be able to read AND append to the bind-mounted
`/mnt/owned.txt` (whose owner is uid 1000). You may edit the id-mapping ranges
(`/app/rootless/subuid`, `/app/rootless/subgid`), the storage driver and engine
settings (`/app/rootless/storage.conf`, `/app/rootless/containers.conf`), and the
run specification (`/app/rootless/run.sh`) — including which user-namespace
mapping the container uses. Do not modify `/app/workload.sh`, and the container
must run unprivileged (not as real root, and without a privileged run spec). The
final state is graded by running your configured invocation as `appuser` and
checking the in-container uid and the owner-only file access.
