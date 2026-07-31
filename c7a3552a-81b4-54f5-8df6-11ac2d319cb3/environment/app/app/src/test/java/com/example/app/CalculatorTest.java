package com.example.app;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.example.core.Calculator;
import org.junit.jupiter.api.Test;

class CalculatorTest {
    @Test
    void checksumIsStable() {
        assertEquals(6562704, Calculator.checksum(new int[] {7, 3, 9, 1, 4}));
    }

    @Test
    void labelIsCoreName() {
        assertEquals("widget-core", Calculator.label());
    }
}
