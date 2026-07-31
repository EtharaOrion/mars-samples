# star30 harden-container-runspec

Container-setup / AR1 long-horizon multi-constraint state. Agent must produce a run spec launching the service under a simultaneous hardening policy (non-root, read-only rootfs + minimal tmpfs, cap-drop ALL, no-new-privileges) that still serves the golden response; naive hardening (read-only without tmpfs) breaks the app. Maturity draft; disposition HOLD:PILOT_REQUIRED.
