# Repair a job pipeline schedule

`/app` contains a tiny batch pipeline. `/app/run.sh` reads `/app/schedule.txt`
(one job name per line, top to bottom) and, for each name, executes the matching
script `/app/jobs/<name>.sh`. The jobs read fixed inputs under `/app/inputs/` and
hand intermediate artifacts to one another through files under `/app/work/`; the
final job publishes `/app/out/result.txt`, and every job records itself by
appending its own name to `/app/out/order.log` as it runs. Each run of
`/app/run.sh` first clears `/app/work` and `/app/out`, so a job that executes
before the jobs producing its inputs will silently read empty intermediate data
and the published result will be wrong even though the run finishes cleanly.

Determine, from the job scripts themselves, which jobs consume the outputs of
which other jobs, then arrange `/app/schedule.txt` so every job runs only after
all jobs producing its inputs have already run, and execute `/app/run.sh`. When
you are done, `/app/out/result.txt` must be the byte-exact artifact the pipeline
produces under a correct order (four lines of the form `stats_sum=<int>`,
`weighted=<int>`, `base=<int>`, `result=<int>`, each terminated by a newline),
and `/app/out/order.log` must list every job exactly once in an order in which no
job appears before a job that produces one of its inputs. You may only change the
schedule: leave every file under `/app/jobs/` and `/app/inputs/` byte-for-byte
unchanged.
