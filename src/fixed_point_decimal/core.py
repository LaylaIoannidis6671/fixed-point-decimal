"""Fixed-point decimal arithmetic over plain integers.

Design decisions, stated plainly
---------------------------------
* Precision is set once per instance and is immutable. Two operands with
  different precisions are reconciled by aligning the one with fewer
  decimal places up, never by rounding the more precise one down. This
  means mixing precisions is exact (no data is discarded).
* Division is the only operation that can produce a non-terminating
  expansion (e.g. 1 / 3). We round half-to-even (banker's rounding) at the
  target precision, because it is symmetric and matches what users of
  financial fixed-point libraries expect.
* We never silently return a result whose precision differs from its
  operands. Results always carry the maximum of the input precisions; for
  division the result precision is explicit via ``places`` (defaulting to
  the left operand's).
* Comparisons are value-only: a 2-place "1.50" and a 3-place "1.500" are
  equal. This is the only sane rule for fixed point; ordering by precision
  would surprise every caller.
* No floating point is ever constructed during arithmetic. The only time
  floats touch this code is the explicit ``from_float`` constructor, which
  is documented as a lossy bridge for tests and IO glue.
"""

from __future__ import annotations

from math import isfinite


class FixedPoint:
    """A decimal number stored as a plain integer scaled by ``10 ** places``.

    Examples
    --------
    >>> a = FixedPoint("1.25", places=2)
    >>> b = FixedPoint("3", places=2)
    >>> a + b
    FixedPoint('4.25', places=2)
    >>> a * b
    FixedPoint('3.75', places=2)
    >>> (a * b).to_str()
    '3.75'
    """

    __slots__ = ("_units", "places")

    def __init__(self, value, *, places: int):
        """Construct from an integer, a string, or a FixedPoint.

        ``places`` is the number of decimal digits stored after the point and
        is part of the value's identity for display purposes; two values with
        different ``places`` can still be compared and combined.
        """
        if not isinstance(places, int) or places < 0:
            raise ValueError("places must be a non-negative integer")
        self.places = places
        self._units = self._coerce_input(value, places)

    @staticmethod
    def _coerce_input(value, places: int) -> int:
        if isinstance(value, FixedPoint):
            return FixedPoint._align_units(value._units, value.places, places)
        if isinstance(value, int) and not isinstance(value, bool):
            return value * (10 ** places)
        if isinstance(value, str):
            return FixedPoint._parse_str(value, places)
        raise TypeError(
            "FixedPoint accepts int, str, or FixedPoint; got "
            f"{type(value).__name__}"
        )

    @staticmethod
    def _align_units(units: int, src_places: int, dst_places: int) -> int:
        if src_places == dst_places:
            return units
        if src_places < dst_places:
            return units * (10 ** (dst_places - src_places))
        # Aligning to fewer places requires rounding, which would silently
        # discard data. Refuse rather than guess.
        raise ValueError(
            f"cannot align from {src_places} places to {dst_places} places "
            "without loss; construct the target explicitly"
        )

    @staticmethod
    def _parse_str(s: str, places: int) -> int:
        text = s.strip()
        if not text:
            raise ValueError("empty decimal string")
        sign = 1
        if text[0] in "+-":
            if text[0] == "-":
                sign = -1
            text = text[1:]
        if not text:
            raise ValueError(f"malformed decimal string: {s!r}")
        if "." in text:
            if text.count(".") != 1:
                raise ValueError(f"malformed decimal string: {s!r}")
            whole, frac = text.split(".", 1)
        else:
            whole, frac = text, ""
        if whole == "":
            whole = "0"
        if not whole.isdigit():
            raise ValueError(f"malformed decimal string: {s!r}")
        if frac == "":
            frac = "0"
        if not frac.isdigit():
            raise ValueError(f"malformed decimal string: {s!r}")
        raw = int(whole) * (10 ** places)
        if places == 0:
            # Fractional part ignored only when the target precision is zero;
            # this is the one situation where there is genuinely nothing to
            # store, so dropping it is not silent data loss.
            return sign * raw
        if len(frac) == places:
            raw += int(frac)
        elif len(frac) < places:
            raw += int(frac) * (10 ** (places - len(frac)))
        else:
            # More fractional digits than the target precision can hold.
            # Rounding here would make parsing context-dependent; instead we
            # require the caller to truncate explicitly so that the number of
            # digits always matches the declared precision.
            raise ValueError(
                f"string {s!r} has {len(frac)} fractional digits but "
                f"places={places}"
            )
        return sign * raw

    @classmethod
    def from_float(cls, value: float, *, places: int) -> "FixedPoint":
        """Lossy bridge from float.

        Floats cannot represent most decimals exactly, so this constructor
        rounds the float's decimal text representation. It exists for tests
        and IO glue; do not use it as a primary input path.
        """
        if not isfinite(value):
            raise ValueError("cannot construct FixedPoint from non-finite float")
        text = f"{value:.{places + 12}f}"
        if "." in text:
            text = text[: places + text.find(".") + 1]
        return cls(text, places=places)

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    @staticmethod
    def _pair(a: "FixedPoint", b: "FixedPoint"):
        places = max(a.places, b.places)
        au = FixedPoint._align_units(a._units, a.places, places)
        bu = FixedPoint._align_units(b._units, b.places, places)
        return au, bu, places

    def __add__(self, other) -> "FixedPoint":
        if not isinstance(other, FixedPoint):
            return NotImplemented
        au, bu, places = self._pair(self, other)
        return FixedPoint._from_units(au + bu, places)

    def __sub__(self, other) -> "FixedPoint":
        if not isinstance(other, FixedPoint):
            return NotImplemented
        au, bu, places = self._pair(self, other)
        return FixedPoint._from_units(au - bu, places)

    def __mul__(self, other) -> "FixedPoint":
        if not isinstance(other, FixedPoint):
            return NotImplemented
        # The raw product has self.places + other.places fractional digits.
        # We keep all of them, so the result precision is the sum.
        places = self.places + other.places
        return FixedPoint._from_units(self._units * other._units, places)

    def __floordiv__(self, other) -> "FixedPoint":
        """Integer division of the underlying unscaled units.

        Provided because it is exact and unambiguous; ``__truediv__`` is the
        rounding division.
        """
        if not isinstance(other, FixedPoint):
            return NotImplemented
        if other._units == 0:
            raise ZeroDivisionError("FixedPoint floor-divide by zero")
        # Align both to the same scale so the quotient is meaningful.
        au, bu, places = self._pair(self, other)
        return FixedPoint._from_units((au // bu) * (10 ** places), places)

    def __truediv__(self, other) -> "FixedPoint":
        if not isinstance(other, FixedPoint):
            return NotImplemented
        return self.divmod(other)[0]

    def divmod(self, other, *, places: int | None = None) -> tuple["FixedPoint", "FixedPoint"]:
        """Return ``(quotient, remainder)`` for ``self / other``.

        The quotient is rounded half-to-even at ``places`` (defaulting to the
        left operand's precision). The remainder is ``self - quotient * other``
        and carries the same precision as the operands after alignment.
        """
        if not isinstance(other, FixedPoint):
            raise TypeError("divmod requires a FixedPoint divisor")
        if other._units == 0:
            raise ZeroDivisionError("FixedPoint divide by zero")
        au, bu, op_places = self._pair(self, other)
        if places is None:
            places = self.places
        # Multiply numerator by 10**places so the integer quotient lands at
        # the desired scale, then round-to-even the last digit.
        scaled = au * (10 ** places)
        q, r = divmod(scaled, bu)
        twice_r = 2 * r
        if twice_r > bu or (twice_r == bu and (q & 1)):
            q += 1
        quotient = FixedPoint._from_units(q, places)
        # Remainder in the original aligned scale.
        remainder = FixedPoint._from_units((scaled - q * bu) // (10 ** places), op_places)
        return quotient, remainder

    def __neg__(self) -> "FixedPoint":
        return FixedPoint._from_units(-self._units, self.places)

    def __abs__(self) -> "FixedPoint":
        return FixedPoint._from_units(abs(self._units), self.places)

    # ------------------------------------------------------------------
    # Comparisons (value-only; precision is ignored for ordering)
    # ------------------------------------------------------------------

    def _cmp_units(self, other: "FixedPoint") -> int:
        au, bu, _ = self._pair(self, other)
        return (au > bu) - (au < bu)

    def __eq__(self, other) -> bool:
        if not isinstance(other, FixedPoint):
            return NotImplemented
        return self._cmp_units(other) == 0

    def __hash__(self) -> int:
        # Hash by value, not by precision, so 1.50 == 1.500 hashes equal.
        canonical = self._units
        if self.places:
            while self.places and canonical % 10 == 0:
                canonical //= 10
        return hash(("FixedPoint", canonical))

    def __lt__(self, other) -> bool:
        if not isinstance(other, FixedPoint):
            return NotImplemented
        return self._cmp_units(other) < 0

    def __le__(self, other) -> bool:
        if not isinstance(other, FixedPoint):
            return NotImplemented
        return self._cmp_units(other) <= 0

    def __gt__(self, other) -> bool:
        if not isinstance(other, FixedPoint):
            return NotImplemented
        return self._cmp_units(other) > 0

    def __ge__(self, other) -> bool:
        if not isinstance(other, FixedPoint):
            return NotImplemented
        return self._cmp_units(other) >= 0

    # ------------------------------------------------------------------
    # Conversion / repr
    # ------------------------------------------------------------------

    @classmethod
    def _from_units(cls, units: int, places: int) -> "FixedPoint":
        obj = cls.__new__(cls)
        obj.places = places
        obj._units = units
        return obj

    def to_str(self) -> str:
        sign = "-" if self._units < 0 else ""
        units = abs(self._units)
        if self.places == 0:
            return f"{sign}{units}"
        base = 10 ** self.places
        whole, frac = divmod(units, base)
        return f"{sign}{whole}.{frac:0{self.places}d}"

    def to_int(self) -> int:
        """Truncated integer part (toward zero)."""
        base = 10 ** self.places
        if self._units >= 0:
            return self._units // base
        return -((-self._units) // base)

    def to_float(self) -> float:
        """Lossy conversion to float. Avoid for arithmetic; use for IO only."""
        return self._units / (10 ** self.places)

    def __repr__(self) -> str:
        return f"FixedPoint({self.to_str()!r}, places={self.places})"

    def __str__(self) -> str:
        return self.to_str()
