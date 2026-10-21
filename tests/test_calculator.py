"""Unit tests for the calculator module.

Standard-library only: run with

    python3 -m unittest discover -s tests -t . -v
"""

import unittest

from calculator import add, divide, multiply, subtract


class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-2, 3), 1)
        self.assertAlmostEqual(add(0.5, 0.25), 0.75)

    def test_subtract(self):
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(subtract(3, 5), -2)
        self.assertAlmostEqual(subtract(1.5, 0.5), 1.0)

    def test_multiply(self):
        self.assertEqual(multiply(4, 5), 20)
        self.assertEqual(multiply(-4, 5), -20)
        self.assertEqual(multiply(0, 99), 0)

    def test_divide(self):
        self.assertAlmostEqual(divide(10, 2), 5.0)
        self.assertAlmostEqual(divide(7, 2), 3.5)
        self.assertAlmostEqual(divide(-9, 3), -3.0)

    def test_divide_by_zero_raises(self):
        with self.assertRaises(ZeroDivisionError):
            divide(5, 0)

    def test_identity_and_symmetry(self):
        for x in (0, 7, -3, 2.5):
            self.assertEqual(add(x, 0), x)
            self.assertEqual(multiply(x, 1), x)
            self.assertEqual(subtract(x, x), 0)
            self.assertEqual(subtract(0, x), -x)


if __name__ == "__main__":
    unittest.main()
