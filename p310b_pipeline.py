
#!/usr/bin/env python3
"""P3.10b: reconstructed JSON to Lean pipeline test.

This test does not establish historical input provenance.
It does not assume the optimality conclusion.
"""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from lnz_p34d import process
from p310a_audit import audit, AuditError


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_audit_failure(raw, lean, label):
    try:
        audit(raw, lean)
    except AuditError:
        print("REJECTED:", label)
        return
    raise AssertionError("Mutation accepted: " + label)


def run():
    # Reconstructed regression case, not historical input.
    doc = {
        "schema_version": "PENSAI-LNZ-POC-0.2",
        "case_id": "P310B_RECONSTRUCTED",
        "problem": {
            "type": "box_simplex_min",
            "dimension": 2,
            "lo": ["0", "0"],
            "hi": ["1", "1"],
            "coeff": ["1", "2"]
        },
        "certificate": {
            "witness": ["1", "0"],
            "threshold": "1",
            "objective": "1"
        },
        "evidence": {
            "complete": True,
            "noncompensatory_violation": False
        }
    }

    raw = json.dumps(
        doc, separators=(",", ":")
    ).encode("utf-8")

    result = process(raw)
    lean = result["lean_source"]

    check(
        result["verification"] == "VALID",
        "Generator rejected the baseline"
    )

    # Independent comparison of JSON and generated data.
    audit(raw, lean)
    print("DATA_COMPARISON_PASS")

    # Negative test: change the JSON but retain the Lean.
    altered = copy.deepcopy(doc)
    altered["problem"]["coeff"][1] = "3"
    changed_raw = json.dumps(
        altered, separators=(",", ":")
    ).encode("utf-8")

    expect_audit_failure(
        changed_raw, lean, "JSON coefficient tampering"
    )

    # Negative test: change generated Lean but retain JSON.
    altered_lean = lean.replace(
        "((2 : ℚ) / (1 : ℚ))",
        "((3 : ℚ) / (1 : ℚ))",
        1
    )

    check(
        altered_lean != lean,
        "Lean mutation target not found"
    )

    expect_audit_failure(
        raw, altered_lean, "Lean coefficient tampering"
    )

    with tempfile.TemporaryDirectory(
        prefix="lnz_p310b_"
    ) as folder:
        output = Path(folder) / "P310bGenerated.lean"
        output.write_text(lean, encoding="utf-8")

        # Compile the actual generated source.
        subprocess.run(
            ["lake", "env", "lean", str(output)],
            check=True
        )

    print("P310B_PIPELINE_PASS")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(
            "P310B_PIPELINE_FAIL:",
            repr(exc),
            file=sys.stderr
        )
        sys.exit(1)
