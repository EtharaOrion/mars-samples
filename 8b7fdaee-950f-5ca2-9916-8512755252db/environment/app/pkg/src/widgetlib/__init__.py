__version__ = "1.4.2"


def compute(n):
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total + 42
