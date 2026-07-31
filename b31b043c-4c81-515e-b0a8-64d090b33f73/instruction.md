# Cross-compile the release binary for ARM64

The std-only Rust crate at `/app` compiles for this machine's native
architecture today, but the delivery target is 64-bit ARM Linux. Bring the
crate's Cargo toolchain configuration to a working state so that, from `/app`,
the command

    cargo build --release --target aarch64-unknown-linux-gnu

completes successfully (exit status 0) with no network access, and emits a
release executable at

    /app/target/aarch64-unknown-linux-gnu/release/star14

The produced file must be a real ARM64 ELF: its ELF header `e_machine` field
must be `EM_AARCH64` (`0xB7`), i.e. a genuine `aarch64` binary and NOT this
host's native architecture. The already-installed `aarch64-unknown-linux-gnu`
Rust target and cross toolchain are present in the image; only the crate's
build/toolchain configuration is out of shape and must be corrected so linking
resolves against the ARM64 toolchain.

Do not alter or remove any file under `src/` or the crate's `build.rs`: every
`.rs` source file and the build script must remain exactly as shipped. The
graded end state is the ARM64 release binary at the path above (correct
`e_machine`) together with a clean, offline `cargo build --release --target
aarch64-unknown-linux-gnu` exit 0.
