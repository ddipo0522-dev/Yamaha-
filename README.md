# Yamaha-

## Calculator

A small, dependency-free Python module providing four pure arithmetic functions.
The module and its tests use only the Python standard library, so nothing needs
to be installed to use or test them.

### Module: `calculator`

```python
from calculator import add, subtract, multiply, divide
```

| Function | Signature | Returns |
| --- | --- | --- |
| `add` | `add(a: int \| float, b: int \| float) -> int \| float` | the sum `a + b` |
| `subtract` | `subtract(a: int \| float, b: int \| float) -> int \| float` | the difference `a - b` |
| `multiply` | `multiply(a: int \| float, b: int \| float) -> int \| float` | the product `a * b` |
| `divide` | `divide(a: int \| float, b: int \| float) -> float` | the true division `a / b` |

All four functions are pure: no global state, no logging, no I/O.

### Divide by zero

`divide` raises a catchable `ZeroDivisionError` with the message
`"cannot divide by zero"` when the divisor is `0`. It never returns `None`,
`0`, or an infinity for that case.

```python
from calculator import divide

divide(7, 2)   # -> 3.5
divide(1, 0)   # -> raises ZeroDivisionError("cannot divide by zero")
```

### Usage example

```python
from calculator import add, subtract, multiply, divide

print(add(2, 3))        # 5
print(subtract(5, 3))   # 2
print(multiply(4, 5))   # 20
print(divide(7, 2))     # 3.5
```

### Running the tests

From the repository root:

```bash
python3 -m unittest discover -s tests -t . -v
```

The suite can also be run directly:

```bash
python3 -m unittest tests.test_calculator
```

## Factory verification

`hello.txt` at the repository root contains exactly the single line
`Fusion factory verification complete`. It is the Fusion factory's
end-to-end verification artifact: a byte-for-byte predictable file that any
fresh agent or CI run can check with one command.

It is covered by `tests/test_hello_txt.py`, which is part of the same suite:

```bash
python3 -m unittest discover -s tests -t . -v
```
