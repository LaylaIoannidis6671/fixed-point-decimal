import unittest

from fixed_point_decimal import FixedPoint


class ConstructionTests(unittest.TestCase):
    def test_from_int_zero_places(self):
        v = FixedPoint(5, places=0)
        self.assertEqual(v.to_str(), "5")
        self.assertEqual(v.places, 0)

    def test_from_int_positive_places(self):
        v = FixedPoint(3, places=2)
        self.assertEqual(v.to_str(), "3.00")

    def test_from_negative_int(self):
        v = FixedPoint(-7, places=3)
        self.assertEqual(v.to_str(), "-7.000")

    def test_from_str_exact_fraction(self):
        v = FixedPoint("1.25", places=2)
        self.assertEqual(v.to_str(), "1.25")

    def test_from_str_with_explicit_plus(self):
        v = FixedPoint("+0.50", places=2)
        self.assertEqual(v.to_str(), "0.50")

    def test_from_str_short_fraction_pads(self):
        v = FixedPoint("1.5", places=3)
        self.assertEqual(v.to_str(), "1.500")

    def test_from_str_no_fraction(self):
        v = FixedPoint("42", places=2)
        self.assertEqual(v.to_str(), "42.00")

    def test_from_str_too_many_digits_raises(self):
        with self.assertRaises(ValueError):
            FixedPoint("1.234", places=2)

    def test_from_str_empty_raises(self):
        with self.assertRaises(ValueError):
            FixedPoint("", places=2)

    def test_from_str_garbage_raises(self):
        with self.assertRaises(ValueError):
            FixedPoint("1.2x", places=2)

    def test_from_str_double_dot_raises(self):
        with self.assertRaises(ValueError):
            FixedPoint("1..5", places=2)

    def test_from_bool_raises(self):
        with self.assertRaises(TypeError):
            FixedPoint(True, places=2)

    def test_from_float_finite(self):
        v = FixedPoint.from_float(0.125, places=3)
        self.assertEqual(v.to_str(), "0.125")

    def test_from_float_non_finite_raises(self):
        with self.assertRaises(ValueError):
            FixedPoint.from_float(float("inf"), places=2)

    def test_from_fixed_point_aligns_up(self):
        a = FixedPoint("1.50", places=2)
        b = FixedPoint(a, places=3)
        self.assertEqual(b.to_str(), "1.500")

    def test_from_fixed_point_aligning_down_raises(self):
        a = FixedPoint("1.500", places=3)
        with self.assertRaises(ValueError):
            FixedPoint(a, places=2)

    def test_negative_places_rejected(self):
        with self.assertRaises(ValueError):
            FixedPoint(1, places=-1)


class ArithmeticTests(unittest.TestCase):
    def test_add_same_precision(self):
        r = FixedPoint("1.25", places=2) + FixedPoint("0.75", places=2)
        self.assertEqual(r.to_str(), "2.00")
        self.assertEqual(r.places, 2)

    def test_add_different_precision_aligns_up(self):
        r = FixedPoint("1.5", places=1) + FixedPoint("0.05", places=2)
        self.assertEqual(r.to_str(), "1.55")
        self.assertEqual(r.places, 2)

    def test_subtraction_negative_result(self):
        r = FixedPoint("1.00", places=2) - FixedPoint("2.50", places=2)
        self.assertEqual(r.to_str(), "-1.50")

    def test_mul_precision_sums(self):
        r = FixedPoint("1.25", places=2) * FixedPoint("0.50", places=2)
        self.assertEqual(r.to_str(), "0.6250")
        self.assertEqual(r.places, 4)

    def test_mul_by_negative(self):
        r = FixedPoint("1.25", places=2) * FixedPoint("-2", places=2)
        self.assertEqual(r.to_str(), "-2.5000")

    def test_floordiv_integer_division(self):
        r = FixedPoint("10", places=2) // FixedPoint("3", places=2)
        self.assertEqual(r.to_str(), "3.00")

    def test_floordiv_by_zero_raises(self):
        with self.assertRaises(ZeroDivisionError):
            _ = FixedPoint("1", places=2) // FixedPoint("0", places=2)

    def test_truediv_exact(self):
        r = FixedPoint("1.00", places=2) / FixedPoint("4.00", places=2)
        self.assertEqual(r.to_str(), "0.25")
        self.assertEqual(r.places, 2)

    def test_truediv_rounding_half_to_even(self):
        # 1.00 / 8.00 = 0.125; at places=2 this rounds to 0.12 (half-to-even,
        # since the digit before the discarded 5 is 2, even).
        r = FixedPoint("1.00", places=2) / FixedPoint("8.00", places=2)
        self.assertEqual(r.to_str(), "0.12")
        # 3.00 / 8.00 = 0.375; at places=2 the digit before the 5 is 7 (odd),
        # so we round up to 0.38.
        r2 = FixedPoint("3.00", places=2) / FixedPoint("8.00", places=2)
        self.assertEqual(r2.to_str(), "0.38")

    def test_divmod_returns_pair(self):
        q, rem = FixedPoint("10.00", places=2).divmod(FixedPoint("3.00", places=2))
        self.assertEqual(q.to_str(), "3.33")
        self.assertEqual(rem.to_str(), "0.01")

    def test_divmod_explicit_places(self):
        q, _ = FixedPoint("1", places=0).divmod(FixedPoint("3", places=0), places=4)
        self.assertEqual(q.to_str(), "0.3333")

    def test_truediv_by_zero_raises(self):
        with self.assertRaises(ZeroDivisionError):
            _ = FixedPoint("1", places=2) / FixedPoint("0", places=2)

    def test_negation(self):
        v = -FixedPoint("1.25", places=2)
        self.assertEqual(v.to_str(), "-1.25")

    def test_abs_of_negative(self):
        v = abs(FixedPoint("-1.25", places=2))
        self.assertEqual(v.to_str(), "1.25")

    def test_abs_of_positive(self):
        v = abs(FixedPoint("1.25", places=2))
        self.assertEqual(v.to_str(), "1.25")

    def test_arithmetic_with_non_fixed_returns_not_implemented(self):
        with self.assertRaises(TypeError):
            _ = FixedPoint("1", places=2) + 1
        with self.assertRaises(TypeError):
            _ = FixedPoint("1", places=2) * 2


class ComparisonTests(unittest.TestCase):
    def test_equal_same_precision(self):
        self.assertEqual(FixedPoint("1.50", places=2), FixedPoint("1.50", places=2))

    def test_equal_different_precision(self):
        self.assertEqual(FixedPoint("1.50", places=2), FixedPoint("1.500", places=3))

    def test_not_equal(self):
        self.assertNotEqual(FixedPoint("1.50", places=2), FixedPoint("1.51", places=2))

    def test_ordering(self):
        a = FixedPoint("1.00", places=2)
        b = FixedPoint("2.00", places=2)
        self.assertTrue(a < b)
        self.assertTrue(a <= b)
        self.assertFalse(a > b)
        self.assertFalse(a >= b)

    def test_ordering_different_precision(self):
        a = FixedPoint("1.5", places=1)
        b = FixedPoint("1.501", places=3)
        self.assertTrue(a < b)

    def test_hash_equal_for_equal_values(self):
        self.assertEqual(
            hash(FixedPoint("1.50", places=2)),
            hash(FixedPoint("1.500", places=3)),
        )

    def test_hash_unequal_for_unequal_values(self):
        self.assertNotEqual(
            hash(FixedPoint("1.50", places=2)),
            hash(FixedPoint("1.51", places=2)),
        )

    def test_comparison_with_non_fixed_returns_not_implemented(self):
        with self.assertRaises(TypeError):
            _ = FixedPoint("1", places=2) < 1


class ConversionTests(unittest.TestCase):
    def test_to_int_truncates_toward_zero(self):
        self.assertEqual(FixedPoint("-1.99", places=2).to_int(), -1)
        self.assertEqual(FixedPoint("1.99", places=2).to_int(), 1)

    def test_to_float_lossy(self):
        # 0.125 is exactly representable, so this round-trips cleanly.
        self.assertEqual(FixedPoint("0.125", places=3).to_float(), 0.125)

    def test_repr_includes_places(self):
        self.assertEqual(
            repr(FixedPoint("1.5", places=2)),
            "FixedPoint('1.50', places=2)",
        )

    def test_str_matches_to_str(self):
        v = FixedPoint("-1.25", places=2)
        self.assertEqual(str(v), "-1.25")


class ZeroPlacesTests(unittest.TestCase):
    def test_zero_places_arithmetic(self):
        r = FixedPoint("5", places=0) + FixedPoint("3", places=0)
        self.assertEqual(r.to_str(), "8")
        self.assertEqual(r.places, 0)

    def test_mixed_zero_and_nonzero_places(self):
        r = FixedPoint("5", places=0) + FixedPoint("0.25", places=2)
        self.assertEqual(r.to_str(), "5.25")
        self.assertEqual(r.places, 2)


if __name__ == "__main__":
    unittest.main()
