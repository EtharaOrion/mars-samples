"""Pure deterministic helpers used by the build report and the unit tests."""


def square(n):
    return n * n


def sum_squares(values):
    total = 0
    for v in values:
        total += square(v)
    return total


def normalize(name):
    return " ".join(str(name).strip().lower().split())


def checksum(values):
    acc = 0
    for i, v in enumerate(values, start=1):
        acc = (acc * 31 + square(v) + i) % 1000000007
    return acc
