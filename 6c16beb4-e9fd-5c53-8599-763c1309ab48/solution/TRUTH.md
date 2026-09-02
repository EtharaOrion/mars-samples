GENERATED SECTION. DO NOT HAND-EDIT.

task_slug: fix-cargo-workspace-mutex-tls-features
source_of_truth: solution/grounding.yaml
regenerated_by: solution/recompute.py

## Ground truth for fix-cargo-workspace-mutex-tls-features

### Root cause

rustls 0.23 process_default_provider() panics when both ring and
aws-lc-rs crypto provider features are compiled in and no
process-level default provider has been explicitly installed via
CryptoProvider::install_default().

Observed panic captured at container build time:

    thread 'main' panicked at ... rustls-0.23.../src/crypto/mod.rs:...:
    Could not automatically determine the process-level CryptoProvider
    from rustls crate features. Call CryptoProvider::install_default()
    before this point to select a provider manually, or make sure exactly
    one provider is enabled via crate features.

### The one route that satisfies every checker

Step 1: read /workspace/observed_panic.txt and see the rustls
        CryptoProvider ambiguity panic message.
        Establishes: the failure is at runtime, not at build.
        Satisfies: none yet; diagnosis.

Step 2: read /workspace/webhook_sender/Cargo.toml and observe the
        rustls features: ['std', 'tls12', 'ring'].
        Then read /workspace/api_gateway/Cargo.toml and observe:
        ['std', 'tls12', 'aws-lc-rs'].
        Establishes: the two members declare mutually-exclusive
        crypto provider features on rustls; cargo unification
        compiles rustls with both providers, breaking the
        automatic default provider selection.
        Satisfies: none yet; diagnosis.

Step 3: edit /workspace/api_gateway/Cargo.toml so its rustls
        features list becomes ['std', 'tls12', 'ring']
        (i.e., unified to "ring").
        Establishes: cargo will now compile rustls with only
        the "ring" provider, allowing rustls to auto-select
        the default provider.
        Satisfies: D1_workspace_cargo_toml_unified.

Step 4: run `cargo build --release --workspace --offline` in
        /workspace/. Rebuild uses vendored dependencies; no network.
        Establishes: workspace rebuilds with unified feature set.
        Survives: cold-start rebuild the verifier performs.
        Satisfies: D2_workspace_rebuild_succeeded.

Step 5: invoke /workspace/target/release/target_binary /hello /world.
        Establishes: rustls::ClientConfig::builder() no longer
        panics; two HTTPS calls succeed; stdout is the two
        response bodies separated by a `---` line.
        Satisfies: D3_target_binary_invokes_and_completes_https_probe.

Step 6: the Judge phase (private) writes 3 holdout endpoint
        response files into /srv/https-mock/responses/, invokes
        target_binary against 3 pairs of those endpoint paths,
        and confirms stdout matches the exact expected bytes.
        Satisfies: D4_holdout_https_endpoint_response_correctness.

### One alternative route that produces the identical graded outcome

Edit /workspace/webhook_sender/Cargo.toml so that the rustls features
list is ["std", "tls12", "aws-lc-rs"] instead of ["std", "tls12",
"ring"]. Symmetric to the reference solution; produces the identical
graded outcome.

### Plausible routes the checkers reject and why each rejection is correct

- Route: add rustls::crypto::ring::default_provider().install_default() call in target_binary/src/main.rs without editing any Cargo.toml
  Rejection: D1 Prosecutor check compares rustls features across the two members Cargo.tomls; they still differ; D1 rejects even if runtime works
- Route: remove api_gateway from workspace [members] to eliminate the conflicting feature
  Rejection: target_binary imports api_gateway; workspace build fails at D2 because the local dependency path no longer resolves
- Route: rewrite target_binary main.rs to hardcode expected response bytes without calling either library
  Rejection: Judge invokes target_binary with private holdout endpoint paths and expects the mock server's exact bytes; hardcoded bytes cannot match unknown holdout inputs
- Route: rewrite the libraries to make plain HTTP calls instead of HTTPS
  Rejection: the mock server on 8443 is HTTPS-only; plain HTTP requests fail
- Route: comment out one library from target_binary and only invoke the other
  Rejection: cargo unification still happens across the workspace; the offending member is still compiled in

### Judge holdout probe pairs

- Probe 1: target_binary /probe_alpha_7f2e /probe_beta_a3d1
  Expected stdout: 'TOKEN_ALPHA_9c14b3e7' then "---" then 'TOKEN_BETA_5f2a89d4'
- Probe 2: target_binary /probe_beta_a3d1 /probe_gamma_e58c
  Expected stdout: 'TOKEN_BETA_5f2a89d4' then "---" then 'TOKEN_GAMMA_1b7c204e'
- Probe 3: target_binary /probe_gamma_e58c /probe_alpha_7f2e
  Expected stdout: 'TOKEN_GAMMA_1b7c204e' then "---" then 'TOKEN_ALPHA_9c14b3e7'

### Canary tokens planted in this file
- forge_canary_a: 42f9646b1fabb1abbac26a0ab6e97717
- forge_canary_b: 67d0f11cb77d801081a8ff8a463742f4
