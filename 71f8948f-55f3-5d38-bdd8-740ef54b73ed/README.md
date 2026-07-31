# fix-github-actions-ci

Terminal Task, sub_type build-ci-cd, archetype AR5 adversarial option expansion.
A small Python project (calc package + Makefile) ships with a BROKEN
`.github/workflows/ci.yml`. Because `act` and real GitHub runners are offline,
grading uses a self-contained, deterministic in-container `run-workflow`
(stdlib-only) that parses the workflow, orders jobs by `needs:`, applies
declared env and `working-directory`, and runs each step's `run:` block. The
agent may edit ONLY `ci.yml`; several plausible YAML fixes exist but only one
makes `make build` then `make test` run in order with the right env so the
golden artifact and test marker are produced. World-state graded. Red line:
project source, tests, Makefile, and run-workflow stay byte-identical.
Maturity draft; disposition ceiling HOLD:PILOT_REQUIRED.
