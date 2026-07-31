"""Utility helpers used by the sample application."""


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def is_even(number):
    return number % 2 == 0
