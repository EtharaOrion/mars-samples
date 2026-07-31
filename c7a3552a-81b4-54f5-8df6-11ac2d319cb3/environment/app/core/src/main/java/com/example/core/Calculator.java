package com.example.core;

/**
 * Core numeric utilities used by the application layer.
 */
public final class Calculator {
    private Calculator() {
    }

    /** Polynomial rolling checksum over the given samples. */
    public static int checksum(int[] samples) {
        int acc = 0;
        for (int s : samples) {
            acc = acc * 31 + s;
        }
        return acc;
    }

    /** Human-readable identifier for the core module. */
    public static String label() {
        return "widget-core";
    }
}
