# anubis-ledger

A small service package. The runtime configuration lives in
`app/core/config.py` and is validated by `app/selfcheck.py`, which requires the
module constant `CONFIG_REVISION` to equal the release marker tracked in
`app/core/REVISION`.

Run the built-in self check from the repository root:

```
python3 -m app.selfcheck
```

An exit status of `0` means the configuration is consistent with the tracked
release marker.
