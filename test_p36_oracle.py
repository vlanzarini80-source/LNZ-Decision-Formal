
#!/usr/bin/env python3
"""P3.6: independent exact box-simplex oracle tests."""

import copy
import itertools
import json
import random
import unittest
from fractions import Fraction

from lnz_p34d import process, Rejected

VERSION = "PENSAI-LNZ-POC-0.2"


def decimal(q):
    """Convert a rational with finite decimal expansion."""
    q = Fraction(q)
    den = q.denominator
    a = b = 0
    while den % 2 == 0:
        den //= 2
        a += 1
    while den % 5 == 0:
        den //= 5
        b += 1
    if den != 1:
        raise ValueError("nonterminating decimal")
    k = max(a, b)
    num = q.numerator * (10 ** k // q.denominator)
    sign = "-" if num < 0 else ""
    digits = str(abs(num)).zfill(k + 1)
    if k == 0:
        return sign + digits
    return sign + digits[:-k] + "." + digits[-k:].rstrip("0") if digits[-k:].rstrip("0") else sign + digits[:-k]


def make_case(lo, hi, coeff, witness, threshold, objective):
    n = len(lo)
    return {
        "schema_version": VERSION,
        "case_id": "oracle",
        "problem": {
            "type": "box_simplex_min",
            "dimension": n,
            "lo": [decimal(x) for x in lo],
            "hi": [decimal(x) for x in hi],
            "coeff": [decimal(x) for x in coeff],
        },
        "certificate": {
            "witness": [decimal(x) for x in witness],
            "threshold": decimal(threshold),
            "objective": decimal(objective),
        },
        "evidence": {
            "complete": True,
            "noncompensatory_violation": False,
        },
    }


def encode(doc):
    return json.dumps(
        doc, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def independent_optimum(lo, hi, coeff):
    """Enumerate vertices, without using LNZ's verifier."""
    n = len(lo)
    if sum(lo) > 1 or sum(hi) < 1:
        return None

    best = None
    for free in range(n):
        others = [i for i in range(n) if i != free]
        for choices in itertools.product((0, 1), repeat=n - 1):
            x = [Fraction(0)] * n
            for i, side in zip(others, choices):
                x[i] = hi[i] if side else lo[i]
            x[free] = 1 - sum(x[i] for i in others)
            if not lo[free] <= x[free] <= hi[free]:
                continue
            value = sum(coeff[i] * x[i] for i in range(n))
            if best is None or value < best:
                best = value
    return best


def accepted(doc):
    try:
        result = process(encode(doc))
        return result["verification"] == "VALID"
    except Rejected:
        return False


class TestIndependentOracle(unittest.TestCase):

    def test_known_optimum(self):
        lo = [Fraction(0), Fraction(0)]
        hi = [Fraction(1), Fraction(1)]
        coeff = [Fraction(1), Fraction(2)]
        self.assertEqual(
            independent_optimum(lo, hi, coeff), Fraction(1)
        )
        doc = make_case(
            lo, hi, coeff, [Fraction(1), Fraction(0)],
            Fraction(1), Fraction(1)
        )
        self.assertTrue(accepted(doc))

    def test_suboptimal_witness_rejected(self):
        doc = make_case(
            [Fraction(0)] * 2,
            [Fraction(1)] * 2,
            [Fraction(1), Fraction(2)],
            [Fraction(0), Fraction(1)],
            Fraction(1), Fraction(2)
        )
        self.assertEqual(
            independent_optimum(
                [Fraction(0)] * 2,
                [Fraction(1)] * 2,
                [Fraction(1), Fraction(2)]
            ),
            Fraction(1)
        )
        self.assertFalse(accepted(doc))

    def test_fixed_coordinates(self):
        lo = [Fraction(1), Fraction(0)]
        hi = [Fraction(1), Fraction(0)]
        coeff = [Fraction(9), Fraction(-3)]
        doc = make_case(
            lo, hi, coeff,
            [Fraction(1), Fraction(0)],
            Fraction(0), Fraction(9)
        )
        self.assertEqual(
            independent_optimum(lo, hi, coeff), Fraction(9)
        )
        self.assertTrue(accepted(doc))

    def test_fractional_interior(self):
        half = Fraction(1, 2)
        lo = [Fraction(0), Fraction(0)]
        hi = [Fraction(1), Fraction(1)]
        coeff = [half, half]
        doc = make_case(
            lo, hi, coeff, [half, half], half, half
        )
        self.assertEqual(
            independent_optimum(lo, hi, coeff), half
        )
        self.assertTrue(accepted(doc))

    def test_wrong_objective_rejected(self):
        doc = make_case(
            [Fraction(0)] * 2,
            [Fraction(1)] * 2,
            [Fraction(1), Fraction(2)],
            [Fraction(1), Fraction(0)],
            Fraction(1), Fraction(999)
        )
        self.assertFalse(accepted(doc))

    def test_duplicate_json_keys_rejected(self):
        raw = (
            b'{"schema_version":"PENSAI-LNZ-POC-0.2",'
            b'"schema_version":"PENSAI-LNZ-POC-0.2"}'
        )
        with self.assertRaises(Rejected):
            process(raw)

    def test_random_exact_soundness(self):
        rng = random.Random(3601)
        checked = 0
        for _ in range(200):
            n = rng.randint(1, 5)
            lo = [Fraction(rng.randint(0, 2), 4)
                  for _ in range(n)]
            hi = [Fraction(rng.randint(2, 4), 4)
                  for _ in range(n)]
            if any(lo[i] > hi[i] for i in range(n)):
                continue
            optimum = independent_optimum(
                lo, hi,
                [Fraction(0)] * n
            )
            if optimum is None:
                continue

            coeff = [Fraction(rng.randint(-8, 8), 4)
                     for _ in range(n)]
            optimum = independent_optimum(lo, hi, coeff)
            self.assertIsNotNone(optimum)

            # Produce a feasible vertex independently.
            vertices = []
            for free in range(n):
                others = [i for i in range(n) if i != free]
                for sides in itertools.product(
                    (0, 1), repeat=n - 1
                ):
                    w = [Fraction(0)] * n
                    for i, side in zip(others, sides):
                        w[i] = hi[i] if side else lo[i]
                    w[free] = 1 - sum(
                        w[i] for i in others
                    )
                    if lo[free] <= w[free] <= hi[free]:
                        vertices.append(w)

            w = rng.choice(vertices)
            objective = sum(
                coeff[i] * w[i] for i in range(n)
            )
            lam = Fraction(rng.randint(-8, 8), 4)
            doc = make_case(
                lo, hi, coeff, w, lam, objective
            )
            if accepted(doc):
                self.assertEqual(
                    objective, optimum,
                    "LNZ accepted a suboptimal certificate"
                )
            checked += 1

        self.assertGreaterEqual(checked, 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
