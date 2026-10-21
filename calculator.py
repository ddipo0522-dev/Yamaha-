"""A small, dependency-free calculator module.

This module is the first real code in this repository and sets the project
conventions: standard-library only at runtime, explicit type hints, and pure
functions with no global state or I/O.
"""

__all__ = ["add", "subtract", "multiply", "divide"]


def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of ``a`` and ``b``."""
    return a + b


def subtract(a: int | float, b: int | float) -> int | float:
    """Return the difference of ``a`` and ``b``."""
    return a - b


def multiply(a: int | float, b: int | float) -> int | float:
    """Return the product of ``a`` and ``b``."""
    return a * b


def divide(a: int | float, b: int | float) -> float:
    """Return the true division of ``a`` by ``b``.

    Raises:
        ZeroDivisionError: if ``b`` is zero.
    """
    if b == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return a / b
