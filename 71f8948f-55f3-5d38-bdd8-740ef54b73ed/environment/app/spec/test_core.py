import unittest

from calc.core import square, sum_squares, normalize, checksum


class TestCore(unittest.TestCase):
    def test_square(self):
        self.assertEqual(square(12), 144)
        self.assertEqual(square(0), 0)

    def test_sum_squares(self):
        self.assertEqual(sum_squares(range(1, 11)), 385)
        self.assertEqual(sum_squares([]), 0)

    def test_normalize(self):
        self.assertEqual(normalize("  Hello   World "), "hello world")

    def test_checksum(self):
        self.assertEqual(checksum(range(1, 11)), checksum(list(range(1, 11))))


if __name__ == "__main__":
    unittest.main()
