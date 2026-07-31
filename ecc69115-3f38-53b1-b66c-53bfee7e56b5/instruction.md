# Build the Go monorepo through its dependency graph

The repository at `/app` is a small Go monorepo built by a provided graph
runner, `build.py`. Targets are declared in Bazel-style `BUILD` files under
`libs/mathx/`, `libs/report/`, and `cmd/app/`: each declares its `srcs` and the
other targets it depends on via `deps`. The runner compiles every target inside
an isolated staging tree that contains only the sources reachable through that
target's declared dependency edges, then builds targets in dependency order.
Running `python3 build.py //...` from `/app` must build every target
successfully. The produced binary at `bazel-bin/cmd/app/app`, when run, must
print exactly

    app total=34 sum=34 product=3003

and the `//libs/mathx:mathx_test` target must build and pass.

As shipped, the dependency graph does not describe what the code actually
imports, so the runner cannot assemble a complete staging tree for the
downstream targets and the build stops before the binary is produced. Repair the
graph so that `python3 build.py //...` builds all targets in correct dependency
order, the binary prints the line above, and the test target passes. Confine
your changes to the `BUILD` graph files; the Go sources under `libs/` and
`cmd/`, the test file, and the `build.py` runner must remain exactly as shipped,
byte for byte.
