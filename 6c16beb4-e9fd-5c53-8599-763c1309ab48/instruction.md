# Fix the target_binary that panics at first HTTPS call

The Rust cargo workspace at `/workspace` was built at container build time.
`cargo build --release --workspace` completed cleanly (see
`/workspace/prebuild_log.txt`). The workspace contains three members:

- `webhook_sender` — library that wraps an HTTPS GET via rustls
- `api_gateway` — library that wraps an HTTPS GET via rustls
- `target_binary` — an executable that calls into both libraries

When `/workspace/target/release/target_binary` is invoked with two endpoint
paths, it panics before completing the first HTTPS call. The build-time
capture is in `/workspace/observed_panic.txt`.

Your job is to fix the workspace so that

```
/workspace/target/release/target_binary <path1> <path2>
```

runs cleanly, makes the two HTTPS calls to the container-local HTTPS mock
server on `https://localhost:8443`, and prints the two response bodies
separated by a line containing exactly `---`.

You can exercise your fix using the public endpoints already served by the
mock: `/hello`, `/world`, `/status`. For example:

```
/workspace/target/release/target_binary /hello /world
```

Once you exit, the verifier will:

1. Reinstall your fixed workspace (rebuild from your edits on a clean checkout).
2. Invoke `target_binary` against endpoint paths of the verifier's choosing
   (the verifier will not tell you which ones).
3. Grade both that the binary invokes cleanly AND that the printed responses
   match the mock server's canonical bytes on those endpoints.

Constraints:

- No external network access. All Rust crate dependencies are already
  vendored under `/workspace/vendor/` and `/workspace/.cargo/config.toml`
  points cargo at that vendor directory.
- The HTTPS mock server on `localhost:8443` and its root cert in the
  container trust store are the only HTTPS surface you can rely on.
- You may edit any file under `/workspace/`. You may not modify anything
  under `/srv/https-mock/`.
- `target_binary` must remain invocable as
  `/workspace/target/release/target_binary <path1> <path2>` after your fix.
