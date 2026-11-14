
#!/usr/bin/env python3
"""P319.1 - Independent seven-field integrity audit.

Checks JSON-to-Lean data preservation, complete source
identity and adversarial mutations.

Does NOT execute Lean or certify arbitrary documents.
"""

import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from lnz_p34d import (
    load_and_validate,
    verify,
    generate,
    process,
)
from p310a_audit import (
    audit,
    parse_json,
    parse_lean,
    AuditError,
)

FIELDS = (
    "dimension",
    "lo",
    "hi",
    "coeff",
    "witness",
    "threshold",
    "objective",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def encode(doc):
    return json.dumps(
        doc,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(original_raw, candidate_source):
    """Check every field and exact generated-source identity."""

    expected = parse_json(original_raw)
    observed = parse_lean(candidate_source)

    for field in FIELDS:
        require(
            expected[field] == observed[field],
            "FIELD_MISMATCH:" + field,
        )

    require(
        audit(original_raw, candidate_source) is True,
        "INDEPENDENT_AUDIT_FAILED",
    )

    regenerated = process(original_raw)["lean_source"]

    require(
        candidate_source == regenerated,
        "SOURCE_IDENTITY_MISMATCH",
    )

    return {
        "input_sha256": digest(original_raw),
        "source_sha256": digest(
            candidate_source.encode("utf-8")
        ),
    }


def sample():
    """Valid test fixture, not a claimed research result."""

    return {
        "schema_version": "PENSAI-LNZ-POC-0.2",
        "case_id": "P319_TEST",
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


def mutate(values, field):
    """Change one mathematical field in the generated data."""

    changed = copy.deepcopy(values)

    if field == "dimension":
        for key in ("lo", "hi", "coeff", "witness"):
            changed[key] = changed[key][:-1]

    elif field in ("lo", "hi", "coeff", "witness"):
        changed[field][0] += Fraction(1)

    elif field in ("threshold", "objective"):
        changed[field] += Fraction(1)

    else:
        raise AssertionError("UNKNOWN_FIELD:" + field)

    return changed


def must_reject(original_raw, candidate, label):
    """A mismatch must be rejected by the independent audit."""

    try:
        audit(original_raw, candidate)
    except AuditError:
        print("FIELD_MUTATION_REJECTED:", label)
        return

    raise AssertionError(
        "INDEPENDENT_AUDIT_ACCEPTED_MUTATION:" + label
    )


def must_reject_identity(original_raw, candidate, label):
    """Reject changes even when the seven fields are unchanged."""

    try:
        check(original_raw, candidate)
    except (AuditError, AssertionError):
        print("SOURCE_MUTATION_REJECTED:", label)
        return

    raise AssertionError(
        "SOURCE_MUTATION_ACCEPTED:" + label
    )


def main():
    raw = encode(sample())

    doc, values = load_and_validate(raw)

    require(
        doc["problem"]["dimension"] == len(values["lo"]),
        "BASELINE_DIMENSION_ERROR",
    )

    # Independently invoke the generator's mathematical
    # validation. No expected objective is supplied to it.
    verify(values)

    source = process(raw)["lean_source"]
    baseline = check(raw, source)

    print("BASELINE_INTEGRITY_PASS")

    rejected_fields = []

    for field in FIELDS:
        changed = mutate(values, field)
        candidate = generate(changed)

        require(
            candidate != source,
            "MUTATION_DID_NOT_CHANGE_SOURCE:" + field,
        )

        observed = parse_lean(candidate)
        expected = parse_json(raw)

        require(
            observed[field] != expected[field],
            "TARGET_FIELD_NOT_CHANGED:" + field,
        )

        must_reject(raw, candidate, field)
        rejected_fields.append(field)

    require(
        tuple(rejected_fields) == FIELDS,
        "INCOMPLETE_FIELD_COVERAGE",
    )

    # A non-mathematical source modification must also fail.
    extra = source + "\n-- unauthorized modification\n"

    require(
        parse_lean(extra) == parse_lean(source),
        "UNEXPECTED_DATA_CHANGE",
    )

    must_reject_identity(
        raw,
        extra,
        "appended_source",
    )

    # The exact source must remain accepted.
    check(raw, source)

    report = {
        **baseline,
        "status": "PYTHON_INTEGRITY_AUDIT_PASS",
        "checked_fields": list(FIELDS),
        "field_mutations_rejected": len(rejected_fields),
        "source_mutations_rejected": 1,
        "total_mutations_rejected": len(rejected_fields) + 1,
        "lean_executed": False,
        "lean_semantics_certified": False,
        "arbitrary_documents_verified": False,
        "scope": "Structured box-simplex JSON-to-Lean integrity",
    }

    Path("p319_integrity_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("P319_PYTHON_INTEGRITY_PASS")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
