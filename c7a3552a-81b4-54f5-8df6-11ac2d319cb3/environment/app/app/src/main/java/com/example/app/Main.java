package com.example.app;

import com.example.core.Calculator;

/**
 * Production entrypoint. Reports the core label and the checksum of the
 * canonical sample vector.
 */
public final class Main {
    private static final int[] SAMPLES = {7, 3, 9, 1, 4};

    private Main() {
    }

    public static void main(String[] args) {
        System.out.println(Calculator.label() + " checksum=" + Calculator.checksum(SAMPLES));
    }
}
