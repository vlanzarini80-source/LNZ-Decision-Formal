
#!/usr/bin/env python3
"""P319.2: prepare positive and negative Lean checks.

Uses the existing generator and exact rational arithmetic.
Does not assume the desired optimality theorem.
"""

import argparse
import copy
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

from lnz_p34d import (
    Rejected,
    generate,
    load_and_validate,
    process,
    verify,
)
from p310a_audit import audit
from p319_integrity_audit import sample, encode, check


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_forbidden(source):
    forbidden = re.search(
        r"\b(sorry|admit|sorryAx|unsafe|axiom)\b",
        source,
    )
    require(
        forbidden is None,
        "FORBIDDEN_LEAN_CONSTRUCT",
    )


def prepare():
    raw = encode(sample())
    _, values = load_and_validate(raw)

    # Positive certificate: validate and generate.
    verify(values)
    positive = process(raw)["lean_source"]

    check(raw, positive)
    require(
        audit(raw, positive) is True,
        "POSITIVE_DATA_AUDIT_FAILED",
    )
    check_forbidden(positive)

    # Negative certificate: preserve all constraints
    # but change the claimed objective.
    negative_values = copy.deepcopy(values)
    negative_values["objective"] += Fraction(1)

    require(
        negative_values["objective"] != values["objective"],
        "NEGATIVE_MUTATION_NOT_APPLIED",
    )

    # The original mathematical verifier must reject it.
    try:
        verify(negative_values)
    except Rejected:
        pass
    else:
        raise AssertionError(
            "INVALID_OBJECTIVE_ACCEPTED_BY_PYTHON"
        )

    # Generate the invalid certificate without running
    # the Python verifier, so Lean itself can reject it.
    negative = generate(negative_values)
    check_forbidden(negative)

    require(
        negative != positive,
        "IDENTICAL_POSITIVE_AND_NEGATIVE_SOURCES",
    )

    Path("P319PositiveGenerated.lean").write_text(
        positive,
        encoding="utf-8",
    )
    Path("P319NegativeGenerated.lean").write_text(
        negative,
        encoding="utf-8",
    )

    # The Lean source imports and theorem name are those
    # of the existing P34 generator. Compile each variant
    # under the expected module filename in CI.
    report = {
        "status": "PREPARED_NOT_LEAN_VERIFIED",
        "input_sha256": digest(raw),
        "positive_sha256": digest(
            positive.encode("utf-8")
        ),
        "negative_sha256": digest(
            negative.encode("utf-8")
        ),
        "negative_mutation": "objective_plus_one",
        "python_rejected_negative": True,
        "lean_positive_compiled": False,
        "lean_negative_rejected": False,
        "certified": False,
    }

    Path("p319_lean_bridge_report.json").write_text(
        json.dumps(
            report, indent=2, sort_keys=True
        ) + "\n",
        encoding="utf-8",
    )

    print("P319_LEAN_BRIDGE_PREPARED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["prepare"],
    )
    args = parser.parse_args()

    if args.command == "prepare":
        prepare()


if __name__ == "__main__":
    main()
