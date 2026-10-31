
#!/usr/bin/env python3
"""P3.12a: JSON -> Python -> Lean source integrity test.

This checks exact data preservation and deterministic
generation. It does not compile Lean or prove Python
and Lean implementation soundness.
"""

import copy
import hashlib
import json

from lnz_p34d import process
from p310a_audit import audit, AuditError
from test_p311_independent import baseline, certificate_oracle


def encode(doc):
    return json.dumps(
        doc, separators=(",", ":")
    ).encode("utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    doc = baseline()
    raw = encode(doc)

    require(
        certificate_oracle(doc),
        "Independent certificate oracle rejected input"
    )

    result = process(raw)

    require(
        result["verification"] == "VALID",
        "Python verifier rejected valid input"
    )

    require(
        result["sha256_input"] == hashlib.sha256(raw).hexdigest(),
        "Incorrect input SHA256"
    )

    lean = result["lean_source"]

    require(
        audit(raw, lean) is True,
        "JSON/Lean data mismatch"
    )

    again = process(raw)

    require(
        again["lean_source"] == lean,
        "Non-deterministic Lean generation"
    )

    require(
        again["sha256_input"] == result["sha256_input"],
        "Non-deterministic input hash"
    )

    mutated = copy.deepcopy(doc)
    mutated["problem"]["coeff"][0] = "4"

    try:
        audit(encode(mutated), lean)
    except AuditError:
        pass
    else:
        raise AssertionError(
            "Old Lean certificate accepted for changed JSON"
        )

    with open("P312Generated.lean", "w", encoding="utf-8") as f:
        f.write(lean)

    with open("p312_input.sha256", "w", encoding="ascii") as f:
        f.write(result["sha256_input"] + "\n")

    print("P312_JSON_PYTHON_AUDIT_PASS")
    print("P312_DETERMINISTIC_GENERATION_PASS")
    print("P312_MUTATION_REJECTED")
    print("P312_LEAN_SOURCE_GENERATED")
    print("SHA256:", result["sha256_input"])


if __name__ == "__main__":
    main()
