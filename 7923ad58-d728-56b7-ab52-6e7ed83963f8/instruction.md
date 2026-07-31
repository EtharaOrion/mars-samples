# Make the release build compute the right result

The Rust crate at `/app` builds and runs today, but the program prints the wrong
answer. Bring the crate to a correct, working state so that, from `/app`:
`cargo build --release` completes successfully, the produced release binary
(`./target/release/star18`) runs and prints, on a single line with no other
output, the crate's checksum of its built-in input; and `cargo test` passes.
The one and only correct printed line is:

    202739307150

Only the crate's build/feature configuration is out of shape - the program logic
is already correct for the intended code path. Do not alter or remove any file
under `src/` or `tests/`: every `.rs` source and test file must remain exactly as
shipped and must pass unchanged. The graded output is the single decimal integer
line above, produced by the release binary, together with a passing test run.
