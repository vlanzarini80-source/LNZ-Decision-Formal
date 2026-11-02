
#!/usr/bin/env python3
"""P3.13a: audit sperimentale dei confini di fiducia.

Non dimostra la correttezza generale di Python o Lean.
Non usa codice proprietario PENSAI.
"""

import copy
import hashlib
import json

from lnz_p34d import process, Rejected
from p310a_audit import audit, AuditError
from test_p311_independent import baseline


def encode(doc):
    return json.dumps(
        doc, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def must_reject(raw):
    try:
        process(raw)
    except Rejected:
        return
    raise AssertionError("Invalid input accepted")


def main():
    doc = baseline()
    raw = encode(doc)
    result = process(raw)

    require(
        result["verification"] == "VALID",
        "Valid baseline rejected"
    )

    require(
        result["sha256_input"] == hashlib.sha256(raw).hexdigest(),
        "Incorrect SHA256"
    )

    require(
        audit(raw, result["lean_source"]) is True,
        "Data preservation audit failed"
    )

    print("P313_BASELINE_PASS")

    # Identical mathematical data, different JSON bytes.
    alternate = json.dumps(
        doc, indent=2, ensure_ascii=False
    ).encode("utf-8")

    alternate_result = process(alternate)

    require(
        raw != alternate,
        "Fixtures unexpectedly identical"
    )
    require(
        result["sha256_input"] != alternate_result["sha256_input"],
        "SHA256 failed to distinguish byte representations"
    )
    require(
        result["lean_source"] == alternate_result["lean_source"],
        "Equivalent data produced different Lean source"
    )

    print("P313_BYTE_IDENTITY_PASS")

    # Evidence flags influence illustrative policy,
    # but do not enter the mathematical Lean certificate.
    modified = copy.deepcopy(doc)
    modified["evidence"]["complete"] = False
    changed = process(encode(modified))

    require(
        changed["illustrative_policy"] == "HOLD",
        "Incomplete evidence did not produce HOLD"
    )
    require(
        changed["lean_source"] == result["lean_source"],
        "Evidence unexpectedly changed Lean mathematics"
    )

    modified["evidence"]["noncompensatory_violation"] = True
    stopped = process(encode(modified))

    require(
        stopped["illustrative_policy"] == "STOP",
        "Noncompensatory violation did not produce STOP"
    )
    require(
        stopped["lean_source"] == result["lean_source"],
        "Policy flags unexpectedly changed Lean mathematics"
    )

    print("P313_POLICY_SEPARATION_PASS")

    # The instance identity is not embedded in the theorem.
    renamed = copy.deepcopy(doc)
    renamed["case_id"] = "DIFFERENT_CASE"
    renamed_result = process(encode(renamed))

    require(
        renamed_result["lean_source"] == result["lean_source"],
        "Case ID unexpectedly changed Lean source"
    )
    require(
        renamed_result["sha256_input"] != result["sha256_input"],
        "Case identity mutation not reflected in input hash"
    )

    print("P313_CASE_ID_BOUNDARY_PASS")

    # Adversarial rejection checks.
    must_reject(raw.replace(b'"dimension":3', b'"dimension":true'))

    duplicate = raw.replace(
        b'"schema_version":',
        b'"schema_version":"DUPLICATE",'
        b'"schema_version":',
        1
    )
    must_reject(duplicate)

    invalid = copy.deepcopy(doc)
    invalid["certificate"]["objective"] = "999"
    must_reject(encode(invalid))

    print("P313_REJECTION_PASS")
    print("P313A_TRUST_BOUNDARY_TESTS_PASS")


if __name__ == "__main__":
    main()
