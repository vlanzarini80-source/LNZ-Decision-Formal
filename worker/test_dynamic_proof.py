import unittest
from dynamic_proof import build, audit

class DynamicProofTests(unittest.TestCase):
    def test_target_stable(self):
        a, h = build("reverse_append", ["rfl"])
        b, j = build("reverse_append", ["simp"])
        self.assertEqual(h, j)
        self.assertNotEqual(a, b)
    def test_unknown_target(self):
        with self.assertRaises(ValueError):
            build("True", ["trivial"])
    def test_injection(self):
        for t in ["sorry", "admit", "simp\naxiom fake : False", "run_tac", "exact False.elim"]:
            with self.assertRaises(ValueError):
                build("reverse_append", [t])
    def test_budget(self):
        with self.assertRaises(ValueError):
            build("reverse_append", ["simp"] * 17)
    def test_axioms(self):
        self.assertFalse(audit("'lnz_candidate' depends on axioms: [sorryAx]"))
        self.assertFalse(audit("'lnz_candidate' depends on axioms: [fake]"))
        self.assertFalse(audit("fake log"))
        self.assertTrue(audit("'lnz_candidate' does not depend on any axioms"))
