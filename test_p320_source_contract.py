
#!/usr/bin/env python3
"""P320.1 deterministic positive and adversarial tests."""

import copy
import json
import unittest

from lnz_p34d import process
from p320_source_contract import (
    build,
    canonical,
    verify_contract,
    ContractError,
)

BASE = {
    "schema_version": "PENSAI-LNZ-POC-0.2",
    "case_id": "P320_TEST",
    "problem": {
        "type": "box_simplex_min",
        "dimension": 3,
        "lo": ["0", "0", "0"],
        "hi": ["1", "1", "1"],
        "coeff": ["1", "2", "3"],
    },
    "certificate": {
        "witness": ["1", "0", "0"],
        "threshold": "1",
        "objective": "1",
    },
    "evidence": {
        "complete": True,
        "noncompensatory_violation": False,
    },
}


def encoded(doc):
    return canonical(doc)


def contract_bytes(source, formal):
    return canonical(build(source, formal))


class BindingTests(unittest.TestCase):

    def setUp(self):
        self.source = encoded(BASE)
        self.formal = encoded(BASE)
        self.contract = contract_bytes(
            self.source, self.formal
        )
        self.lean = process(
            self.formal
        )["lean_source"].encode("utf-8")

    def check_rejected(
        self,
        source=None,
        formal=None,
        contract=None,
        lean=None,
    ):
        with self.assertRaises(
            (ContractError, ValueError)
        ):
            verify_contract(
                self.source if source is None else source,
                self.formal if formal is None else formal,
                self.contract if contract is None else contract,
                self.lean if lean is None else lean,
            )

    def test_00_positive(self):
        result = verify_contract(
            self.source,
            self.formal,
            self.contract,
            self.lean,
        )
        self.assertEqual(
            result["status"], "BOUND_SYNTACTIC"
        )
        self.assertFalse(result["certified"])
        self.assertFalse(result["lean_executed"])
        self.assertFalse(
            result["document_semantics_certified"]
        )

    def test_01_source_changed(self):
        doc = copy.deepcopy(BASE)
        doc["problem"]["coeff"][0] = "4"
        self.check_rejected(source=encoded(doc))

    def test_02_formal_changed(self):
        doc = copy.deepcopy(BASE)
        doc["problem"]["coeff"][0] = "4"
        self.check_rejected(formal=encoded(doc))

    def test_03_objective_changed(self):
        doc = copy.deepcopy(BASE)
        doc["certificate"]["objective"] = "2"
        self.check_rejected(formal=encoded(doc))

    def test_04_witness_changed(self):
        doc = copy.deepcopy(BASE)
        doc["certificate"]["witness"] = [
            "0", "1", "0"
        ]
        self.check_rejected(formal=encoded(doc))

    def test_05_domain_changed(self):
        doc = copy.deepcopy(BASE)
        doc["problem"]["hi"][0] = "0.5"
        self.check_rejected(formal=encoded(doc))

    def test_06_dimension_changed(self):
        doc = copy.deepcopy(BASE)
        doc["problem"]["dimension"] = 2
        for key in ("lo", "hi", "coeff"):
            doc["problem"][key] = doc[
                "problem"
            ][key][:2]
        doc["certificate"]["witness"] = doc[
            "certificate"
        ]["witness"][:2]
        self.check_rejected(formal=encoded(doc))

    def test_07_contract_hash_forged(self):
        contract = json.loads(self.contract)
        contract["source"]["sha256"] = "0" * 64
        self.check_rejected(
            contract=encoded(contract)
        )

    def test_08_relation_forged(self):
        contract = json.loads(self.contract)
        contract["relation"] = "FORMAL_EQUIV"
        self.check_rejected(
            contract=encoded(contract)
        )

    def test_09_attestation_forged(self):
        contract = json.loads(self.contract)
        contract["attestation"] = {
            "name": "user"
        }
        self.check_rejected(
            contract=encoded(contract)
        )

    def test_10_irrelevant_lean_proof(self):
        self.check_rejected(
            lean=(
                b"import Mathlib\n"
                b"theorem irrelevant : True := trivial\n"
            )
        )

    def test_11_duplicate_contract_key(self):
        changed = (
            self.contract[:-1]
            + b',"schema":"fake"}'
        )
        self.check_rejected(contract=changed)

    def test_12_coordinated_change_old_contract(self):
        doc = copy.deepcopy(BASE)
        doc["problem"]["coeff"][2] = "7"
        changed = encoded(doc)
        self.check_rejected(
            source=changed,
            formal=changed,
        )

    def test_13_unestablished_claim(self):
        doc = copy.deepcopy(BASE)
        doc["problem"]["coeff"][2] = "7"
        changed = encoded(doc)
        contract = contract_bytes(
            self.source, changed
        )
        self.check_rejected(
            formal=changed,
            contract=contract,
        )

    def test_14_unknown_contract_field(self):
        contract = json.loads(self.contract)
        contract["verified"] = True
        self.check_rejected(
            contract=encoded(contract)
        )

    def test_15_missing_lean_source(self):
        with self.assertRaises(ContractError):
            verify_contract(
                self.source,
                self.formal,
                self.contract,
                None,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
