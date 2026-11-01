
#!/usr/bin/env python3
"""
P3.12c.1 - Adversarial parser and generator tests.

Scope:
- JSON byte parsing and schema validation
- Exact rational input validation
- Certificate rejection
- Deterministic Lean generation
- Independent JSON/Lean data comparison

No changes to Lean theorems.
No claim of formal Python verification.
"""

import copy
import hashlib
import json

from lnz_p34d import process
from p310a_audit import audit, AuditError
from test_p311_independent import baseline


def encode(doc):
    return json.dumps(
        doc, separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_rejection(name, raw):
    try:
        process(raw)
    except (ValueError, UnicodeError, TypeError):
        print("REJECTED:", name)
        return

    raise AssertionError(
        "Invalid input accepted: " + name
    )


def mutate(name, change):
    doc = copy.deepcopy(baseline())
    change(doc)
    expect_rejection(name, encode(doc))


def test_parser():
    original = encode(baseline())

    expect_rejection(
        "invalid UTF-8",
        b"\xff\xfe\xfa"
    )

    expect_rejection(
        "truncated JSON",
        original[:-1]
    )

    expect_rejection(
        "oversized JSON",
        b" " * (1024 * 1024 + 1)
    )

    expect_rejection(
        "duplicate JSON keys",
        b'{"schema_version":"x",'
        b'"schema_version":"y"}'
    )

    expect_rejection(
        "JSON top-level array",
        b"[]"
    )

    expect_rejection(
        "JSON null",
        b"null"
    )

    expect_rejection(
        "JSON NaN",
        b'{"value":NaN}'
    )

    print("P312C1_PARSER_PASS")


def test_schema():
    mutate(
        "unexpected root field",
        lambda d: d.update({"unexpected": 1})
    )

    mutate(
        "missing certificate",
        lambda d: d.pop("certificate")
    )

    mutate(
        "invalid schema version",
        lambda d: d.update(
            {"schema_version": "INVALID"}
        )
    )

    mutate(
        "boolean dimension",
        lambda d: d["problem"].update(
            {"dimension": True}
        )
    )

    mutate(
        "zero dimension",
        lambda d: d["problem"].update(
            {"dimension": 0}
        )
    )

    mutate(
        "dimension above limit",
        lambda d: d["problem"].update(
            {"dimension": 201}
        )
    )

    mutate(
        "incorrect vector length",
        lambda d: d["problem"].update(
            {"coeff": ["1"]}
        )
    )

    mutate(
        "nonboolean evidence",
        lambda d: d["evidence"].update(
            {"complete": "true"}
        )
    )

    print("P312C1_SCHEMA_PASS")


def test_numeric_parser():
    invalid = [
        "1e0",
        "+1",
        "01",
        "1.",
        ".5",
        "1.0",
        "-0",
        "-0.0",
        "NaN",
        "Infinity",
        " 1",
        "1 ",
        "1/2",
        "",
    ]

    for value in invalid:
        mutate(
            "noncanonical number " + repr(value),
            lambda d, x=value: d["problem"][
                "coeff"
            ].__setitem__(0, x)
        )

    mutate(
        "JSON number instead of string",
        lambda d: d["problem"][
            "coeff"
        ].__setitem__(0, 1)
    )

    mutate(
        "numeric precision limit",
        lambda d: d["problem"][
            "coeff"
        ].__setitem__(0, "9" * 81)
    )

    print("P312C1_NUMERIC_PASS")


def test_certificate():
    mutate(
        "witness violates simplex",
        lambda d: d["certificate"].update(
            {"witness": ["1", "1", "0"]}
        )
    )

    mutate(
        "witness violates box",
        lambda d: d["certificate"].update(
            {"witness": ["2", "0", "-1"]}
        )
    )

    mutate(
        "incorrect objective",
        lambda d: d["certificate"].update(
            {"objective": "2"}
        )
    )

    mutate(
        "incorrect threshold",
        lambda d: d["certificate"].update(
            {"threshold": "0"}
        )
    )

    mutate(
        "invalid lower bound",
        lambda d: d["problem"][
            "lo"
        ].__setitem__(0, "2")
    )

    mutate(
        "invalid upper bound",
        lambda d: d["problem"][
            "hi"
        ].__setitem__(0, "-1")
    )

    print("P312C1_CERTIFICATE_PASS")


def test_generation():
    raw = encode(baseline())

    first = process(raw)
    second = process(raw)

    check(
        first["verification"] == "VALID",
        "Baseline rejected"
    )

    check(
        first["sha256_input"]
        == hashlib.sha256(raw).hexdigest(),
        "Incorrect original-byte hash"
    )

    check(
        first["lean_source"]
        == second["lean_source"],
        "Non-deterministic Lean generation"
    )

    check(
        audit(raw, first["lean_source"]) is True,
        "Independent data audit failed"
    )

    changed = copy.deepcopy(baseline())
    changed["problem"]["coeff"][0] = "4"

    try:
        audit(
            encode(changed),
            first["lean_source"]
        )
    except AuditError:
        pass
    else:
        raise AssertionError(
            "Modified JSON matched old Lean certificate"
        )

    check(
        "sorry" not in first["lean_source"],
        "Generated source contains sorry"
    )

    check(
        "axiom " not in first["lean_source"],
        "Generated source contains axiom declaration"
    )

    print("P312C1_GENERATOR_PASS")


def main():
    test_parser()
    test_schema()
    test_numeric_parser()
    test_certificate()
    test_generation()

    print("P312C1_ADVERSARIAL_PASS")


if __name__ == "__main__":
    main()
