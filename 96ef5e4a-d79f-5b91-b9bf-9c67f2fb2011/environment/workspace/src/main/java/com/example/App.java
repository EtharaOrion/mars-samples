package com.example;

public final class App {

    private App() {
    }

    public static String greet(String name) {
        if (name == null || name.isEmpty()) {
            return "Hello, world!";
        }
        return "Hello, " + name + "!";
    }

    public static int add(int a, int b) {
        return Math.addExact(a, b);
    }

    public static void main(String[] args) {
        System.out.println(greet(args.length == 0 ? null : args[0]));
    }
}
