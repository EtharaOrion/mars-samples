# Make the build reflect the sources

The C project at `/app` builds an executable named `app` by running `make` from
`/app`. The project is compiled from the sources under `src/` and the headers
under `include/`, and the build recipe lives in `/app/Makefile`. Running `make`
must produce an `app` whose behavior matches the current source tree: when run,
`./app` must print exactly

    app coeff-model v2.3.1 compute(12)=996

Right now the build machinery does not correctly track which compiled artifacts
depend on which inputs, so a plain `make` can finish successfully while leaving
`app` out of sync with the headers it is built from. Repair the build so that
`make` always rebuilds whatever is affected by a changed input and the resulting
binary faithfully reflects the current sources. Confine your changes to the
build configuration in `/app/Makefile`; the C sources under `src/` and the
headers under `include/` must remain exactly as shipped, byte for byte.
