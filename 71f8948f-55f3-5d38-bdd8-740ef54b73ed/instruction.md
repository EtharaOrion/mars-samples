# Repair the GitHub Actions CI workflow

The repository at `/app` is a small Python project (the `calc` package with a
`Makefile`) whose continuous-integration pipeline is defined in
`.github/workflows/ci.yml`. This environment has no network access to GitHub and
`act` is not installed, so the pipeline is executed by a bundled offline runner
`/app/run-workflow`: from `/app` it runs `python3 run-workflow
.github/workflows/ci.yml`, which parses the workflow, orders the jobs by their
`needs:`, exports the workflow/job/step `env:`, honors each step's
`working-directory:`, and executes every step's `run:` block in order, stopping
with a non-zero exit as soon as any step fails. The workflow is meant to run the
project's build (`make build`) and then its tests (`make test`).

The workflow is currently broken and does not complete. Edit **only**
`.github/workflows/ci.yml` so that running `python3 run-workflow
.github/workflows/ci.yml` from `/app` finishes successfully (exit code 0) with
the build running before the tests and with the version environment visible to
the build. A correct end state is: the build step produces `/app/out/app.txt`
whose exact contents are the five lines `app-report v2.3.1`,
`sum_squares(1..10)=385`, `square(12)=144`, `checksum=390983325`, `status=ok`
(each followed by a newline), and the test step produces the marker
`/app/out/tests.ok`. Do not modify the project source, the tests, the `Makefile`,
or `run-workflow`; only the workflow YAML may change.
