
#!/usr/bin/env python3
"""Adversarial checks against actual P320.2 CI evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from p3202_bound_lean import check, read


class BoundEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("p3202-source.json")
        cls.formal = Path("p3202-formal.json")
        cls.log = Path("p3202-positive.log")
        cls.exit_code = Path("p3202-exit.txt")

        for p in (
            cls.source, cls.formal,
            cls.log, cls.exit_code
        ):
            if not p.is_file():
                raise RuntimeError(
                    "MISSING_REAL_CI_EVIDENCE:" + str(p)
                )

    def baseline(self):
        return check(
            self.source, self.formal,
            self.log, self.exit_code
        )

    def test_00_actual_positive(self):
        result = self.baseline()
        self.assertEqual(
            result["status"],
            "BOUND_AND_FORMALLY_PROVED",
        )
        self.assertFalse(
            result["document_semantics_certified"]
        )

    def test_01_swapped_document(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "source.json"
            p.write_bytes(read(self.source) + b" ")
            with self.assertRaises(ValueError):
                check(
                    p, self.formal,
                    self.log, self.exit_code
                )

    def test_02_swapped_formal(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "formal.json"
            p.write_bytes(read(self.formal) + b" ")
            with self.assertRaises(ValueError):
                check(
                    self.source, p,
                    self.log, self.exit_code
                )

    def test_03_nonzero_lean_exit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "exit.txt"
            p.write_text("1\n")
            with self.assertRaisesRegex(
                ValueError, "LEAN_EXIT_NONZERO"
            ):
                check(
                    self.source, self.formal,
                    self.log, p
                )

    def test_04_injected_axiom(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.txt"
            log = read(self.log).decode("utf-8")
            log = log.replace(
                "Quot.sound]",
                "Quot.sound, sorryAx]",
            )
            self.assertNotEqual(
                log.encode(), read(self.log)
            )
            p.write_text(log)
            with self.assertRaises(ValueError):
                check(
                    self.source, self.formal,
                    p, self.exit_code
                )

    def test_05_extra_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.txt"
            p.write_bytes(
                read(self.log)
                + b"\nerror: injected\n"
            )
            with self.assertRaisesRegex(
                ValueError, "LEAN_DIAGNOSTIC"
            ):
                check(
                    self.source, self.formal,
                    p, self.exit_code
                )

    def test_06_changed_lean_source(self):
        original = read("P3202Generated.lean")

        def fake_read(path):
            if str(path) == "P3202Generated.lean":
                return original + b"\n-- altered\n"
            return read(path)

        with patch(
            "p3202_bound_lean.read",
            side_effect=fake_read
        ):
            with self.assertRaises(ValueError):
                self.baseline()

    def test_07_changed_contract(self):
        original = read("p3202-contract.json")

        def fake_read(path):
            if str(path) == "p3202-contract.json":
                return original + b" "
            return read(path)

        with patch(
            "p3202_bound_lean.read",
            side_effect=fake_read
        ):
            with self.assertRaises(ValueError):
                self.baseline()

    def test_08_changed_manifest(self):
        original = json.loads(
            read("p3202-manifest.json")
        )
        original["lean_sha256"] = "0" * 64

        def fake_read(path):
            if str(path) == "p3202-manifest.json":
                return json.dumps(original).encode()
            return read(path)

        with patch(
            "p3202_bound_lean.read",
            side_effect=fake_read
        ):
            with self.assertRaises(ValueError):
                self.baseline()


if __name__ == "__main__":
    unittest.main(verbosity=2)
