
#!/usr/bin/env python3
"""P320.4a: adversarial evidence-authenticity probe.

Checks whether synthetic Lean output is accepted as evidence.
This is a vulnerability test, NOT a Lean proof.
"""
import os
import tempfile
import unittest
from pathlib import Path

from p3203_dual_audit import document
from p320_source_contract import canonical
from p3202_bound_lean import prepare, check


class EvidenceAuthenticityProbe(unittest.TestCase):

    def test_synthetic_log_is_not_independent_proof(self):
        original = Path.cwd()

        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)

                doc = document(
                    ["1", "2", "3"],
                    ["1", "0", "0"],
                    "1",
                    "P3204_A",
                )
                raw = canonical(doc)

                Path("source.json").write_bytes(raw)
                Path("formal.json").write_bytes(raw)

                prepare("source.json", "formal.json")

                # Deliberately fabricated evidence.
                # Lean is NOT executed by this test.
                Path("positive.log").write_text(
                    "'LNZ.p34_instance_optimal' "
                    "depends on axioms: "
                    "[propext, Classical.choice, Quot.sound]\n",
                    encoding="utf-8",
                )
                Path("exit.txt").write_text(
                    "0\n", encoding="utf-8"
                )

                result = check(
                    "source.json",
                    "formal.json",
                    "positive.log",
                    "exit.txt",
                )

                # This assertion detects the trust weakness:
                # acceptance without an actual Lean invocation.
                self.assertEqual(
                    result["status"],
                    "BOUND_AND_FORMALLY_PROVED",
                )
                self.assertTrue(result["lean_executed"])

                print(
                    "P3204_EVIDENCE_SPOOFING_DEMONSTRATED"
                )

            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
