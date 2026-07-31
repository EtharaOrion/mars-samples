# Recover the lost core configuration

The git repository at `/app` lost work after a bad `git reset`. The runtime
configuration file `app/core/config.py` is missing from the working tree, and
several abandoned drafts of that same file are floating around in the
repository's object store. Exactly one of those drafts is the correct one: the
version whose module constant `CONFIG_REVISION` matches the release marker
tracked in `app/core/REVISION`, so that running `python3 -m app.selfcheck` from
`/app` exits `0`. The other drafts carry the wrong release marker and must not
be used.

Restore `app/core/config.py` to that correct version and commit it on the
`main` branch. When you are done, `HEAD` must be on `main`, `git fsck` must
report no corruption, and no other tracked file may be added, removed, or
modified. Do not prune, garbage-collect, or otherwise discard any unrelated
history that currently survives in the repository.
