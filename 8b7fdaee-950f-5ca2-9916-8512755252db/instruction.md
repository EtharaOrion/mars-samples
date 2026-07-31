# Package, publish locally, and install widgetlib offline

The directory `/app/pkg` holds the complete source of a small pure-Python
distribution named `widgetlib` (a standard `pyproject.toml` plus a `src/` layout).
This machine has **no network access** and cannot reach PyPI or any remote index,
so every step must be performed offline using only tools already present in the
image (`pip`, `build`, `setuptools`, and `wheel` are installed). You must take the
shipped source through the full packaging pipeline yourself: build a wheel from
`/app/pkg`, make that wheel available through a local package index / find-links
location on this machine, and then install `widgetlib` **from that local
location** into a fresh virtual environment. Do not modify anything under
`/app/pkg`; the source must remain byte-for-byte identical, and the installed
package must be produced by actually building and installing it (not by copying or
hand-editing files to fake the result).

Produce exactly this end state. (1) A built wheel file named
`widgetlib-1.4.2-py3-none-any.whl` must exist in the directory `/app/wheelhouse`.
(2) A Python virtual environment must exist at `/app/.venv` with `widgetlib`
installed into it as a proper distribution, such that
`/app/.venv/bin/python -c "import widgetlib"` succeeds, `widgetlib.__version__`
equals the string `"1.4.2"`, and `widgetlib.compute(7)` returns the integer
`182`. The wheel's metadata version must be `1.4.2`, matching the installed
distribution reported by the virtual environment's own interpreter.
