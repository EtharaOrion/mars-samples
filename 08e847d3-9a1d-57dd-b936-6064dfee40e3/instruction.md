# Summarize service log events

The directory `/app/logs` contains several `.log` files. Every non-empty line
has the form `<timestamp> <LEVEL> <service> <message...>`, where `<LEVEL>` is one
of `INFO`, `WARN`, or `ERROR`. The `<service>` field is normally a single bare
token, but when a service name contains spaces it is written as a single
double-quoted string, for example `"billing service"`. The message is free text
that runs to the end of the line.

Produce a JSON report at `/app/report.json` that counts, per service, how many
non-`INFO` events (that is, `WARN` or `ERROR`) that service produced across all
log files. The report must be a single JSON object with exactly two keys:
`counts`, an object mapping each service that produced at least one non-`INFO`
event to its integer count, and `total_non_info`, the total number of non-`INFO`
events across every service. Service names must be the full names, with quoted
names carrying their internal spaces and without the surrounding quotes. Do not
alter any file under `/app/logs`.
