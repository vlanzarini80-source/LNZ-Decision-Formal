import hashlib
import unittest
from autonomous_search import search

def receipt(source, status, diagnostic=""):
    return dict(source_hash=hashlib.sha256(source.encode()).hexdigest(),status=status,diagnostic=diagnostic)

class SearchTests(unittest.TestCase):
    def test_repair(self):
        def generate(c):
            return '["simp"]' if c["diagnostics"] else '["rfl"]'
        def verify(s):
            return receipt(s,"ACCEPTED" if "  simp\n" in s else "REJECTED","failed tactic")
        r=search("reverse_append",generate,verify)
        self.assertEqual(r["status"],"RUNNER_ACCEPTANCE_UNATTESTED")
        self.assertEqual(len(r["trace"]),2)
        self.assertFalse(r["certified"])
    def test_budget(self):
        r=search("reverse_append",lambda c:'["rfl"]',lambda s:receipt(s,"REJECTED"),3)
        self.assertEqual(r["status"],"BUDGET_EXHAUSTED")
        self.assertEqual(len(r["trace"]),3)
    def test_forged_receipt(self):
        r=search("reverse_append",lambda c:'["simp"]',lambda s:dict(source_hash="wrong",status="ACCEPTED"))
        self.assertEqual(r["status"],"INVALID_RECEIPT")
    def test_invalid_candidate(self):
        r=search("reverse_append",lambda c:'["sorry"]',lambda s:self.fail("must not execute"),2)
        self.assertEqual(r["status"],"BUDGET_EXHAUSTED")
    def test_unavailable(self):
        r=search("reverse_append",lambda c:'["simp"]',lambda s:receipt(s,"UNAVAILABLE"))
        self.assertEqual(r["status"],"VERIFIER_UNAVAILABLE")
