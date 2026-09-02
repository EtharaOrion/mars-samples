GENERATED SECTION. DO NOT HAND-EDIT.

task_slug: fix-go-mod-replace-vendor-desync-v2
source_of_truth: solution/grounding.yaml
regenerated_by: solution/recompute.py

## The single most important insight

The Go build fails because the module identity that `/workspace/myapp/go.mod` names in its `replace` directive
(`example.com/mylib`) does not match the module identity that the local replace target actually declares in its own
`go.mod` (`example.com/mylib-WRONG`). The `replace` directive says `example.com/mylib => ../mylib`, so the toolchain
opens `/workspace/mylib/go.mod`, reads its `module` line, and refuses to bind the local tree to the requested import
path. Every subsequent `go` command re-fires the same diagnostic.

The trap is that the failing command runs in `/workspace/myapp` and the error message names `example.com/mylib`, so a
naive read points the agent at the root project. But root `go.mod` is not broken: its module identity is correct, its
import graph is correct, and its `replace` line points at exactly the local path a proper local library would sit at.
The single broken byte range is the `-WRONG` suffix in `/workspace/mylib/go.mod`. The agent that repeatedly runs
`go mod vendor` and `go mod tidy` in `/workspace/myapp` never converges because there is no convergence path from
that directory: the mismatched declaration lives one level over.

## The ideal solve, step by step

1. **Read `/workspace/observed_error.txt` all the way through.** The captured diagnostic names both module identities
   explicitly: `pointed at module example.com/mylib-WRONG (want example.com/mylib)`. Whichever exact wording the
   installed Go version prints, the two module strings the diagnostic contrasts are the two candidates for the fix.

2. **Open `/workspace/myapp/go.mod` and confirm the replace directive.** It should read something like:

       replace example.com/mylib => ../mylib

   The replacement path is a relative local path. That is where the toolchain looks for the module.

3. **Open `/workspace/mylib/go.mod`.** Its module directive reads:

       module example.com/mylib-WRONG

   Compare against the replace target the root project declared. The declared module identity has a `-WRONG` suffix
   that does not belong. That is the byte range to edit.

4. **Rewrite the module line to `module example.com/mylib`.** Leave `go 1.22` and every other byte of the file alone.
   Do not add, remove, or reorder any other line. The single-line edit is the whole fix.

5. **Verify locally.** From `/workspace/myapp`, run in order:

       go mod verify
       go build ./...
       go test -count=1 ./...

   All three commands must exit 0. The tests exercise `mylib.Greet` and `mylib.Farewell` through the fixed replace
   link, so a passing test run also confirms the replace-target binding actually landed and did not silently regress.

## Traps that catch agents that are not thinking carefully

- **Trap: run `go mod vendor` in a loop.** The vendor command fails with the same replacement-module diagnostic
  because it must resolve the local target before writing the vendor tree. Re-running does not change the byte on
  disk that is broken. `go mod tidy` behaves the same way. There is no vendoring path to convergence while the local
  target names the wrong module.

- **Trap: delete the `replace` directive from root go.mod.** With the directive gone, `go build` tries to fetch
  `example.com/mylib` from `GOPROXY`. The container has `GOPROXY=off` and no network egress, so the fetch fails with
  a proxy or dial error. Even if the fetch somehow succeeded, the grader's static invariant check on the root go.mod
  requires the exact `replace example.com/mylib => ../mylib` directive to remain present.

- **Trap: rename the root module.** Editing the root `go.mod` module line to `example.com/mylib-WRONG` (chasing the
  diagnostic) breaks root module identity. The grader static-parses the root module declaration and rejects any value
  other than `example.com/myapp`.

- **Trap: swap the replace target to a public module.** Rewriting the replace line to point at a remote module
  fails because the container has no network, and it also fails the invariant check that requires the replace
  target to remain `../mylib`.

- **Trap: drop a precompiled `myapp` binary into `$PATH`.** The grader runs `go build ./...` and `go test ./...`
  against the source tree in `/workspace/myapp`, not against any prebuilt binary. A precompiled artifact does not
  satisfy `go build ./...` because the toolchain re-compiles from source. `go test -count=1` also skips the test
  result cache, so a pre-warmed cache would not help either.

## The one route that satisfies every checker

Path b (edit `/workspace/mylib/go.mod` so its module declaration reads `module example.com/mylib`) is the whole fix.
It preserves the root module identity, preserves the replace directive, keeps the local target at `../mylib`, and
makes every `go` command in `/workspace/myapp` resolve cleanly. The diff is a single line.

### Canary tokens planted in this file
- forge_canary_a: FORGE_HOLDOUT_CANARY_331AF3B8B6FC6C0711891ED280327ECC
- forge_canary_b_reference: FORGE_HOLDOUT_CANARY_14330E99269C28A986832E9955C7D4B6
