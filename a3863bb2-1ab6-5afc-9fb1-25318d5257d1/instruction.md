# Repair the two-tier container launch

Inside `/app` sits a layered launch script, `run_pipeline.sh`. Its job: spin up
one *host-tier* ("outer") container which itself reaches back to the running
Docker engine, assembles the image described under `/app/nested/`, and then
launches that assembled image as a second-tier ("nested") container. The
nested container is the only thing that emits the sentinel line:

```
NESTED-OK sum=70 sha=1dc225e4bf52ce88
```

Right now the launch script is broken: the outer tier cannot talk to the engine
and never reaches the nested build, so nothing is produced. Your job is to mend
only the outer-tier plumbing in `run_pipeline.sh` — which base the outer tier
uses, how it is granted access to the Docker engine, and where it looks for the
nested build context — so that a full run reaches this state:

- an image tagged from `NESTED_IMAGE` (default `star26-nested:v1`) has been
  assembled out of `/app/nested/`;
- a container named from `NESTED_NAME` (default `star26-nested-ctr`) was spawned
  from that very image and its recorded log is precisely the sentinel line;
- the file `out/result.txt` holds precisely that sentinel line, captured from
  the nested container's own output.

Treat everything under `/app/nested/` (its `Dockerfile`, `compute.sh`, and
`values.txt`) as read-only — do not touch a single byte of it. Grading is
satisfied only by an authentic nested-container run; synthesising the sentinel
by any shortcut that skips spawning the nested container does not count.
