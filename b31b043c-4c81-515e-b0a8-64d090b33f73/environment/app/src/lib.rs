pub mod arch {
    #[cfg(target_arch = "aarch64")]
    pub fn label() -> &'static str {
        "aarch64"
    }

    #[cfg(target_arch = "x86_64")]
    pub fn label() -> &'static str {
        "x86_64"
    }

    #[cfg(not(any(target_arch = "aarch64", target_arch = "x86_64")))]
    pub fn label() -> &'static str {
        "other"
    }
}

pub fn banner() -> String {
    format!("star14/{}", arch::label())
}
