"""Tiny sample application module (clean of banned tokens)."""


def greet(name):
    return "hello, " + name


def total(values):
    result = 0
    for value in values:
        result += value
    return result
