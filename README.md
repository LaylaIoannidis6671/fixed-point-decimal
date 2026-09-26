# fixed-point-decimal

Decimal arithmetic with a fixed number of digits after the decimal point, stored as plain integers.

```python
from fixed_point_decimal import FixedPoint

a = FixedPoint("1.25", places=2)
b = FixedPoint("0.05", places=2)
print((a + b).to_str())      # 1.30
print((a * b).to_str())      # 0.0625 (places=4)
q, r = a.divmod(b)           # quotient + remainder
print(q.to_str(), r.to_str())
```

## Why this exists

The standard library's `decimal.Decimal` is exact and capable, but it carries a context object, signal handling, and configurable rounding modes that are overkill when the only requirement is "add, subtract, multiply, and divide money-like numbers without floating-point error." This library stores each value as a single Python `int` scaled by `10 ** places`, so arithmetic is one or two integer operations and there is no global state to reason about.

The trade-off is that precision is per-instance and immutable, so every result carries the precision its operands demand (addition uses the wider of the two; multiplication sums them; division rounds to a configurable target). There is no global context that silently picks one for you.

## The awkward edge

Two `FixedPoint` values with different `places` can be compared and combined, but only by aligning the *less* precise one up (e.g. `1.5` at places=1 becomes `1.500` at places=3 when added to a places=3 value). Aligning the *more* precise one down would silently discard digits, so that direction raises `ValueError`. If you need to truncate, do it explicitly by constructing a new value and accepting the loss.

Division is the only operation that can produce a non-terminating expansion (e.g. `1 / 3`). The result is rounded half-to-even (banker's rounding) at the target precision, which defaults to the left operand's `places`. Pass `places=` to `divmod` if you need more or fewer digits.

## Exported names

- `FixedPoint` — the only public class, in `fixed_point_decimal.core`, re-exported from `fixed_point_decimal`.

Constructor: `FixedPoint(value, *, places)` where `value` is an `int`, a `str` (must have at most `places` fractional digits — excess digits raise rather than round), or another `FixedPoint`.

Methods: `to_str()`, `to_int()` (truncates toward zero), `to_float()` (lossy), `divmod(other, *, places=None)` returning `(quotient, remainder)`.

Operators: `+ - * / //` between two `FixedPoint` values; unary `-` and `abs()`; all six comparisons (`== < <= > >=`), value-only, so `1.50` at places=2 equals `1.500` at places=3.
