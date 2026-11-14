
#!/usr/bin/env python3
"""P319.3 adversarial audit of Lean certificate evidence.

Checks exact generated inputs, field differences,
reported Lean axioms, and negative failure classification.

Does not certify arbitrary documents or JSON provenance.
"""

import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

from lnz_p34d import load_and_validate, process, generate
from p310a_audit import parse_lean
from p319_integrity_audit import sample, encode

ALLOWED_AXIOMS = frozenset({
    "propext",
    "Classical.choice",
    "Quot.sound",
})

FIELDS = (
    "dimension",
    "lo",
    "hi",
    "coeff",
    "witness",
    "threshold",
    "objective",
)

AXIOM_PATTERN = re.compile(
    r"'LNZ\.p34_instance_optimal' depends on axioms:"
    r"\s*\[([^\]]*)\]"
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(source):
    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()


def read(path):
    return Path(path).read_text(encoding="utf-8")


def axioms(log):
    matches = AXIOM_PATTERN.findall(log)
    require(
        len(matches) == 1,
        "MISSING_OR_DUPLICATE_AXIOM_REPORT",
    )
    items = [
        item.strip()
        for item in matches[0].split(",")
    ]
    require(
        len(items) == len(set(items)),
        "DUPLICATE_AXIOM",
    )
    return frozenset(items)


def audit_evidence(positive_log, negative_log,
                   report, positive, negative):

    # Check that both sources match the recorded hashes.
    require(
        sha256(positive) == report["positive_sha256"],
        "POSITIVE_HASH_MISMATCH",
    )
    require(
        sha256(negative) == report["negative_sha256"],
        "NEGATIVE_HASH_MISMATCH",
    )

    # Independent parser checks the mathematical fields.
    pos = parse_lean(positive)
    neg = parse_lean(negative)

    changed = [
        field for field in FIELDS
        if pos[field] != neg[field]
    ]

    require(
        changed == ["objective"],
        "UNEXPECTED_MATHEMATICAL_MUTATION",
    )

    require(
        neg["objective"] - pos["objective"] == Fraction(1),
        "WRONG_OBJECTIVE_MUTATION",
    )

    # Compare complete source with independently
    # regenerated canonical source.
    raw = encode(sample())
    _, values = load_and_validate(raw)

    expected_positive = process(raw)["lean_source"]

    changed_values = {
        key: (
            list(value)
            if isinstance(value, list)
            else value
        )
        for key, value in values.items()
    }
    changed_values["objective"] += Fraction(1)

    expected_negative = generate(changed_values)

    require(
        positive == expected_positive,
        "POSITIVE_SOURCE_NOT_CANONICAL",
    )
    require(
        negative == expected_negative,
        "NEGATIVE_SOURCE_NOT_CANONICAL",
    )

    # Positive Lean theorem must have only
    # the permitted foundational axioms.
    positive_axioms = axioms(positive_log)

    require(
        positive_axioms == ALLOWED_AXIOMS,
        "POSITIVE_AXIOM_SET_MISMATCH",
    )

    require(
        "error:" not in positive_log,
        "POSITIVE_LEAN_ERROR",
    )

    # Negative proof must fail in the expected
    # mathematical validity branch.
    require(
        "error: unsolved goals" in negative_log,
        "NEGATIVE_NOT_UNSOLVED_GOAL",
    )

    require(
        re.search(
            r"(?m)^\s*case right\.right\.left\s*$"
            r"\s*⊢ False\s*$",
            negative_log,
        ) is not None,
        "EXPECTED_FALSE_GOAL_MISSING",
    )

    negative_axioms = axioms(negative_log)

    require(
        negative_axioms == (
            ALLOWED_AXIOMS | {"sorryAx"}
        ),
        "NEGATIVE_AXIOM_SET_MISMATCH",
    )

    # Reject any additional Lean error message.
    require(
        len(re.findall(r"\berror:", negative_log)) == 1,
        "ADDITIONAL_NEGATIVE_ERRORS",
    )

    return {
        "status": "P3193_EVIDENCE_AUDIT_PASS",
        "positive_axioms": sorted(positive_axioms),
        "negative_axioms": sorted(negative_axioms),
        "changed_fields": changed,
        "negative_goal": "False",
        "positive_sha256": sha256(positive),
        "negative_sha256": sha256(negative),
        "certified_arbitrary_documents": False,
        "independent_lean_semantic_binding": False,
    }


def must_reject(label, *args):
    try:
        audit_evidence(*args)
    except (AssertionError, KeyError, ValueError):
        print("ADVERSARIAL_REJECTED:", label)
        return
    raise AssertionError("ADVERSARIAL_ACCEPTED:" + label)


def main():
    positive_log = read("p319-positive.log")
    negative_log = read("p319-negative.log")
    positive = read("P319PositiveGenerated.lean")
    negative = read("P319NegativeGenerated.lean")

    report = json.loads(
        read("p319_lean_bridge_report.json")
    )

    require(
        report["negative_mutation"] == "objective_plus_one",
        "INCORRECT_MUTATION_LABEL",
    )
    require(
        report["certified"] is False,
        "FALSE_CERTIFICATION",
    )

    result = audit_evidence(
        positive_log,
        negative_log,
        report,
        positive,
        negative,
    )

    # Mutation tests for the audit itself.
    must_reject(
        "unauthorized_positive_axiom",
        positive_log.replace(
            "Quot.sound]",
            "Quot.sound, sorryAx]",
        ),
        negative_log, report, positive, negative,
    )

    must_reject(
        "missing_false_goal",
        positive_log,
        negative_log.replace("⊢ False", "⊢ True"),
        report, positive, negative,
    )

    must_reject(
        "source_tampering",
        positive_log, negative_log, report,
        positive + "\n-- altered\n", negative,
    )

    must_reject(
        "wrong_negative_axioms",
        positive_log,
        negative_log.replace(
            "sorryAx, ", ""
        ),
        report, positive, negative,
    )

    must_reject(
        "additional_lean_error",
        positive_log,
        negative_log + "\nerror: synthetic failure\n",
        report, positive, negative,
    )

    result["adversarial_tests_rejected"] = 5

    Path("p3193_audit_report.json").write_text(
        json.dumps(
            result, indent=2, sort_keys=True
        ) + "\n",
        encoding="utf-8",
    )

    print("P3193_ADVERSARIAL_AUDIT_PASS")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
