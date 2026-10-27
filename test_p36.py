
import copy
import json
import unittest

from lnz_p34d import (
    process,
    Rejected,
    rational,
    load_and_validate,
    verify,
    generate,
)

BASE = {
    "schema_version": "PENSAI-LNZ-POC-0.2",
    "case_id": "T0",
    "problem": {
        "type": "box_simplex_min",
        "dimension": 2,
        "lo": ["0", "0"],
        "hi": ["1", "1"],
        "coeff": ["1", "2"],
    },
    "certificate": {
        "witness": ["1", "0"],
        "threshold": "1",
        "objective": "1",
    },
    "evidence": {
        "complete": True,
        "noncompensatory_violation": False,
    },
}


def raw(d):
    return json.dumps(
        d, separators=(",", ":")
    ).encode("utf-8")


class P36(unittest.TestCase):

    def test_valid(self):
        self.assertEqual(
            process(raw(BASE))["verification"],
            "VALID",
        )

    def test_duplicate_keys(self):
        bad = raw(BASE).replace(
            b'"case_id":"T0"',
            b'"case_id":"T0","case_id":"T1"',
        )
        with self.assertRaises(Rejected):
            process(bad)

    def test_invalid_utf8(self):
        with self.assertRaises(Rejected):
            process(b"\xff")

    def test_invalid_json(self):
        with self.assertRaises(Rejected):
            process(b"{")

    def test_nan(self):
        bad = raw(BASE).replace(
            b'"dimension":2',
            b'"dimension":NaN',
        )
        with self.assertRaises(Rejected):
            process(bad)

    def test_oversize(self):
        with self.assertRaises(Rejected):
            process(b" " * 1000001)

    def test_wrong_schema(self):
        d = copy.deepcopy(BASE)
        d["schema_version"] = "X"
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_bool_dimension(self):
        d = copy.deepcopy(BASE)
        d["problem"]["dimension"] = True
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_evidence_int(self):
        d = copy.deepcopy(BASE)
        d["evidence"]["complete"] = 1
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_negative_zero(self):
        with self.assertRaises(Rejected):
            rational("-0")

    def test_trailing_zero(self):
        with self.assertRaises(Rejected):
            rational("1.00")

    def test_81_digits(self):
        with self.assertRaises(Rejected):
            rational("1" * 81)

    def test_scientific_notation(self):
        with self.assertRaises(Rejected):
            rational("1e2")

    def test_objective_tamper(self):
        d = copy.deepcopy(BASE)
        d["certificate"]["objective"] = "2"
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_threshold_tamper(self):
        d = copy.deepcopy(BASE)
        d["certificate"]["threshold"] = "-9"
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_witness_tamper(self):
        d = copy.deepcopy(BASE)
        d["certificate"]["witness"] = ["0", "1"]
        d["certificate"]["objective"] = "2"
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_bounds_tamper(self):
        d = copy.deepcopy(BASE)
        d["problem"]["hi"] = ["0", "1"]
        with self.assertRaises(Rejected):
            process(raw(d))

    def test_fixed(self):
        d = copy.deepcopy(BASE)
        d["problem"].update(
            lo=["1", "0"],
            hi=["1", "0"],
            coeff=["9", "-3"],
        )
        d["certificate"].update(
            witness=["1", "0"],
            threshold="0",
            objective="9",
        )
        self.assertEqual(
            process(raw(d))["verification"],
            "VALID",
        )

    def test_fractional(self):
        d = copy.deepcopy(BASE)
        d["problem"]["coeff"] = [
            "0.125", "0.25"
        ]
        d["certificate"].update(
            threshold="0.125",
            objective="0.125",
        )
        self.assertEqual(
            process(raw(d))["verification"],
            "VALID",
        )

    def test_lean_literal_values(self):
        _, values = load_and_validate(raw(BASE))
        verify(values)
        source = generate(values)

        expected = [
            "p34Cert",
            "p34_instance_optimal",
            "valid_box_certificate_optimal",
            "((1 : ℚ) / (1 : ℚ))",
            "((2 : ℚ) / (1 : ℚ))",
        ]

        for value in expected:
            self.assertIn(value, source)

    def test_decimal_length_before_fraction(self):
        with self.assertRaises(Rejected):
            rational("1" * 10000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
