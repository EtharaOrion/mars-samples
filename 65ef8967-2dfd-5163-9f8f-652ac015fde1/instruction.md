# Task: extract column three from a fixed-width pipe-separated data file with embedded tabs and line continuations

## Input

`/workspace/data.txt` contains records in a nominally fixed-width columnar
layout. Fields are separated by the ASCII pipe character `|` and padded with
spaces for visual alignment. Two irregularities complicate the naive
extractor:

1. **Embedded tabs.** Some cells contain literal ASCII horizontal-tab
   characters (`0x09`) *inside* the field bytes. The tabs sit between the
   pipe separators; they do not change the number of pipes per record but
   they do disrupt any byte-offset-based column indexing scheme.

2. **Backslash-newline continuations.** Some records span multiple physical
   lines. A trailing `\` immediately before the newline means the logical
   record continues on the next physical line: the backslash *and* the
   newline are both dropped from the joined record and the next physical
   line's bytes are appended verbatim.

`/workspace/expected_output.txt` shows the exact bytes you must emit for the
public input. Each line is one column-three value with leading and trailing
ASCII space and horizontal-tab characters stripped; interior embedded tabs
and interior runs of spaces are preserved verbatim.

`/workspace/observed_naive_attempt.txt` shows what `awk -F'|' '{print $3}'`
(the naive one-liner) produces on the same input — it drops continuation
tails and emits mangled lines for continued records. Your program must not
share this failure mode.

## Deliverable

Write `/workspace/solve.sh`. When invoked as
`bash /workspace/solve.sh <data_path>`, it must read the data at
`<data_path>` and write to stdout the trimmed column-three value of every
logical record, one per output line, in the order the records appear.

**Tool constraint.** The extraction must be performed by the pinned GNU awk
binary at `/usr/bin/gawk` (invoking it as `gawk` or as `awk` are both
acceptable because `update-alternatives` resolves `awk` to `gawk` in the
image). Do not shell out through the mawk fallback at `/usr/bin/mawk`; do
not use `python`, `perl`, `sed`, `ruby`, `cut`, `column`, or `tr` for the
extraction step; do not hardcode the expected output as a literal string;
do not `cat` any file whose path contains the word `expected` or the path
`/verifier`.

## Grading

The verifier will run your `/workspace/solve.sh` twice — once against
`/workspace/data.txt` and once against a private holdout file
`/verifier/holdout.txt` whose records, embedded-tab positions, continuation
patterns, and column-three values are all different from the public data's
— and assert exact ordered equality of the emitted column-three sequence
against the recorded expected sequence for each input. The verifier also
byte-scans your `/workspace/solve.sh` for the tool-constraint patterns
above.
