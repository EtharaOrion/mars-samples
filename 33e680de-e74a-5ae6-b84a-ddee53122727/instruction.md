# Make the `greet` command available everywhere

A small command-line tool is installed in this machine's image at
`/opt/tools/bin/greet`. It prints exactly the line `hello from greet` to
standard output and exits `0`. The directory holding it is **not** on the
default `PATH`, so typing `greet` currently fails to resolve.

Change the machine's environment so that the bare command `greet` resolves and
runs correctly regardless of how the shell is started. Concretely, after your
change both of the following must succeed with exit status `0` and print
exactly `hello from greet` (a single line, no extra output): running
`bash -lc greet` (a login shell) and running `bash -c greet` (a non-login,
non-interactive shell). You must leave the installed tool at
`/opt/tools/bin/greet` exactly as shipped — do not modify, rewrite, or replace
its contents. Achieve the result by adjusting how commands are located, not by
changing what the tool does.
