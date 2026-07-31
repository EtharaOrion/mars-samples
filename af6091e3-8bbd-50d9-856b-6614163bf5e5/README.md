# rootless-podman-uid-mapping

Container-setup / AR7 ambiguous intermediate state. A half-set rootless Podman
config (empty subuid/subgid ranges, wrong storage driver, and a run spec whose
user-namespace mapping is unset) makes the intended `podman run` fail or map the
container process to the wrong uid, so an owner-only bind-mounted file is
unreachable. Fix is the rootless config + `--userns=keep-id` mapping; grading is
host-side and deterministic. Maturity draft; disposition HOLD:PILOT_REQUIRED.
