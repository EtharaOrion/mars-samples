package com.example;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AppTest {

    @Test
    void greetsWorldOnNull() {
        assertEquals("Hello, world!", App.greet(null));
    }

    @Test
    void greetsWorldOnEmpty() {
        assertEquals("Hello, world!", App.greet(""));
    }

    @Test
    void greetsName() {
        assertEquals("Hello, Mars!", App.greet("Mars"));
    }

    @Test
    void addsTwoIntegers() {
        assertEquals(7, App.add(3, 4));
    }
}
