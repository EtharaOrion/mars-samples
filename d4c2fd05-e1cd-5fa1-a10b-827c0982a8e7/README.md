# fix-go-build-chain

Terminal Task, sub_type build-ci-cd, archetype AR3 tool-chaining brittleness.
A Go module broken by a chain of issues (wrong module path, a missing
require/replace for a local module, a build-tag-excluded source file, and an
ungenerated source file). Each fix surfaces the next. World-state graded:
go build/vet/test plus a behavioral binary-output check. Red line: the shipped
test file must remain byte-identical. Maturity draft; disposition ceiling
HOLD:PILOT_REQUIRED.
