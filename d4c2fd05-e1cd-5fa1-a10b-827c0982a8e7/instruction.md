# Repair the Go build

The Go module at `/app` is currently broken and does not build. Bring it to a
correct, working state so that, from `/app`: `go build ./...` succeeds,
`go vet ./...` reports no problems, `go test ./...` passes, and building the
module's main package produces a `greeter` executable that runs successfully and
prints its greeting line, which reports the library label, what it computes, the
generated version string, and the computed sum of squares of 10.

Fixing one problem tends to reveal the next, so work through the module until all
of the above hold together. Do not alter or remove any existing test file: the
module's tests must remain exactly as shipped and must pass unchanged.
