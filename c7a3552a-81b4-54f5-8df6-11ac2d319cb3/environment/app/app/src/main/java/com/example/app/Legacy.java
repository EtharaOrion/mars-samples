package com.example.app;

/**
 * Deprecated diagnostic entrypoint kept only for historical tooling.
 * It does not exercise the core module and must not ship as the jar's
 * Main-Class.
 */
public final class Legacy {
    private Legacy() {
    }

    public static void main(String[] args) {
        System.out.println("legacy diagnostic mode");
    }
}
