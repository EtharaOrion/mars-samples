# Install a consistent set of local packages into a virtualenv

The directory `/app/wheelhouse` contains a self-contained offline wheelhouse with
several versions of three pure-Python packages: `common`, `alpha`, and `beta`.
`alpha` and `beta` each declare a dependency on a specific major range of
`common`, and different releases of `alpha`/`beta` point at different `common`
ranges, so not every combination can be installed together. A pinned
`/app/requirements.txt` is shipped but it selects releases whose `common`
requirements contradict each other and therefore cannot be co-installed. Your job
is to pick the one release combination of `common`, `alpha`, and `beta` that
installs cleanly together and also satisfies the check described below. Only the
wheels already present in `/app/wheelhouse` may be used; no network access is
required or expected (install with `pip install --no-index --find-links
/app/wheelhouse ...`). Do not modify any file under `/app/wheelhouse`.

Create a Python virtual environment at `/app/.venv` and install exactly one
version each of `common`, `alpha`, and `beta` from the wheelhouse into it so that
all three of the following hold at the same time: (1) inside that virtualenv
`python -c "import alpha, beta, common"` succeeds; (2) the environment is
internally consistent, i.e. running the virtualenv's `pip check` reports no broken
requirements; and (3) running the shipped script with the virtualenv interpreter,
`/app/.venv/bin/python /app/verify.py`, exits with status `0`. The script
`/app/verify.py` imports the three packages and asserts a single computed integer;
your chosen versions must be the ones that make that assertion pass. Leave
`/app/verify.py` and everything under `/app/wheelhouse` unchanged.
