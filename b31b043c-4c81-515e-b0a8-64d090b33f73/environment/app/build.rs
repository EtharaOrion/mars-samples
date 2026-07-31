use std::env;

fn main() {
    let arch = env::var("CARGO_CFG_TARGET_ARCH").unwrap_or_default();
    if arch == "aarch64" {
        let tag = env::var("STAR14_ARCH_TAG").unwrap_or_default();
        if tag != "arm64" {
            panic!(
                "cross build for aarch64 requires STAR14_ARCH_TAG=arm64 \
                 (declare it under [env] in .cargo/config.toml)"
            );
        }
    }
    println!("cargo:rustc-env=STAR14_BUILD_ARCH={}", arch);
    println!("cargo:rerun-if-changed=build.rs");
}
