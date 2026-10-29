
#!/usr/bin/env python3
"""P3.9 candidate: independent JSON-to-generated-Lean DATA audit.

This is not a formal verification of Python, Lean parsing, or generated proofs.

Usage:
    python3 p39_semantic_audit.py input.json generated.lean
    python3 p39_semantic_audit.py --self-test
"""

import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

FIELDS = ("lo", "hi", "coeff", "witness")

ROOT = {
    "schema_version", "case_id", "problem",
    "certificate", "evidence"
}
PROBLEM = {"type", "dimension", "lo", "hi", "coeff"}
CERT = {"witness", "threshold", "objective"}
EVIDENCE = {"complete", "noncompensatory_violation"}

DECIMAL = re.compile(
    r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z"
)

Q = r"\(\((-?\d+) : ℚ\) / \((\d+) : ℚ\)\)"

VECTOR = re.compile(
    r"^  (lo|hi|coeff|witness) := "
    r"\(fun i : Fin (\d+) => "
    r"\(#\[ (.*?)  \]\)\[i\]\),$",
    re.M
)

SCALAR = re.compile(
    r"^  (threshold|objective) := " + Q + r",?$",
    re.M
)

DEF = re.compile(
    r"^private def p34Cert : BoxCertificate (\d+) := \{$",
    re.M
)


class AuditError(ValueError):
    pass


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("duplicate JSON key: " + key)
        result[key] = value
    return result


def keys(obj, expected, label):
    if not isinstance(obj, dict) or set(obj) != expected:
        raise AuditError("wrong keys: " + label)


def decimal_exact(s):
    if not isinstance(s, str) or not DECIMAL.fullmatch(s):
        raise AuditError("invalid decimal")

    if len(s.lstrip("-").replace(".", "")) > 80:
        raise AuditError("oversized decimal")

    if s.startswith("-") and all(
        ch in "0." for ch in s[1:]
    ):
        raise AuditError("negative zero")

    if "." in s and s.endswith("0"):
        raise AuditError("noncanonical decimal")

    negative = s.startswith("-")
    unsigned = s[1:] if negative else s

    whole, dot, fractional = unsigned.partition(".")

    numerator = int(whole + fractional)
    denominator = 10 ** len(fractional) if dot else 1

    return Fraction(
        -numerator if negative else numerator,
        denominator
    )


def parse_json(raw):
    if len(raw) > 1_000_000:
        raise AuditError("oversized input")

    try:
        doc = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda x: (
                _ for _ in ()
            ).throw(AuditError("nonfinite"))
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError("invalid JSON") from exc

    keys(doc, ROOT, "root")

    if doc["schema_version"] != "PENSAI-LNZ-POC-0.2":
        raise AuditError("schema version")

    if (
        not isinstance(doc["case_id"], str)
        or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,64}",
            doc["case_id"]
        )
    ):
        raise AuditError("case ID")

    p = doc["problem"]
    c = doc["certificate"]
    e = doc["evidence"]

    keys(p, PROBLEM, "problem")
    keys(c, CERT, "certificate")
    keys(e, EVIDENCE, "evidence")

    if p["type"] != "box_simplex_min":
        raise AuditError("problem type")

    n = p["dimension"]

    if type(n) is not int or not 1 <= n <= 200:
        raise AuditError("dimension")

    result = {"dimension": n}

    for field in FIELDS:
        src = c if field == "witness" else p

        if (
            not isinstance(src[field], list)
            or len(src[field]) != n
        ):
            raise AuditError(
                "vector length: " + field
            )

        result[field] = [
            decimal_exact(v)
            for v in src[field]
        ]

    for field in ("threshold", "objective"):
        result[field] = decimal_exact(c[field])

    if any(
        type(e[field]) is not bool
        for field in EVIDENCE
    ):
        raise AuditError("evidence flags")

    return result


def q_exact(text):
    match = re.fullmatch(Q, text)

    if match is None:
        raise AuditError(
            "invalid Lean rational: " + text[:70]
        )

    numerator, denominator = map(
        int, match.groups()
    )

    if denominator <= 0:
        raise AuditError("nonpositive denominator")

    return Fraction(numerator, denominator)


def parse_lean(source):
    definitions = list(DEF.finditer(source))

    if len(definitions) != 1:
        raise AuditError(
            "expected exactly one p34Cert definition"
        )

    n = int(definitions[0].group(1))
    start = definitions[0].end()
    end = source.find("\n}", start)

    if end < 0:
        raise AuditError("unclosed certificate")

    block = source[start:end]
    matches = []

    for line in block.splitlines():
        if not line.strip():
            continue

        vector_match = VECTOR.fullmatch(line)
        scalar_match = SCALAR.fullmatch(line)

        if (
            vector_match is None
            and scalar_match is None
        ):
            raise AuditError(
                "unexpected certificate field or syntax"
            )

        matches.append(
            (vector_match, scalar_match)
        )

    if len(matches) != 6:
        raise AuditError(
            "expected six certificate fields"
        )

    result = {"dimension": n}

    for vector_match, scalar_match in matches:
        if vector_match:
            field, vector_n, payload = (
                vector_match.groups()
            )

            if (
                field in result
                or int(vector_n) != n
            ):
                raise AuditError(
                    "duplicate field or dimension mismatch"
                )

            items = (
                payload.split(", ")
                if payload else []
            )

            if len(items) != n:
                raise AuditError(
                    "Lean vector length: " + field
                )

            result[field] = [
                q_exact(item)
                for item in items
            ]

        else:
            field, numerator, denominator = (
                scalar_match.groups()
            )

            if field in result:
                raise AuditError(
                    "duplicate scalar"
                )

            result[field] = q_exact(
                f"(({numerator} : ℚ) / "
                f"({denominator} : ℚ))"
            )

    expected = {
        "dimension",
        *FIELDS,
        "threshold",
        "objective"
    }

    if set(result) != expected:
        raise AuditError("missing fields")

    return result


def audit(raw, lean):
    expected = parse_json(raw)
    observed = parse_lean(lean)

    for field in (
        "dimension",
        *FIELDS,
        "threshold",
        "objective"
    ):
        if observed[field] != expected[field]:
            raise AuditError(
                "semantic mismatch: " + field
            )

    return True


def self_test():
    doc = {
        "schema_version": "PENSAI-LNZ-POC-0.2",
        "case_id": "T0",
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

    raw = json.dumps(doc).encode()

    lean = """import LNZCertificatePayloadP33
namespace LNZ
private def p34Cert : BoxCertificate 2 := {
  lo := (fun i : Fin 2 => (#[ ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))  ])[i]),
  hi := (fun i : Fin 2 => (#[ ((1 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))  ])[i]),
  coeff := (fun i : Fin 2 => (#[ ((1 : ℚ) / (1 : ℚ)), ((2 : ℚ) / (1 : ℚ))  ])[i]),
  witness := (fun i : Fin 2 => (#[ ((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))  ])[i]),
  threshold := ((1 : ℚ) / (1 : ℚ)),
  objective := ((1 : ℚ) / (1 : ℚ))
}
"""

    audit(raw, lean)

    mutations = [
        lean.replace(
            "((2 : ℚ)", "((3 : ℚ)"
        ),
        lean.replace(
            "BoxCertificate 2",
            "BoxCertificate 3"
        ),
        lean.replace(
            "threshold := ((1 : ℚ)",
            "threshold := ((2 : ℚ)"
        ),
        lean.replace(
            "witness :=",
            "unknown :="
        )
    ]

    for changed in mutations:
        try:
            audit(raw, changed)
        except AuditError:
            continue

        raise AssertionError(
            "mutation incorrectly accepted"
        )

    print(
        "P39_SELF_TEST_PASS: "
        "baseline accepted, 4 mutations rejected"
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "json_file",
        nargs="?"
    )
    parser.add_argument(
        "lean_file",
        nargs="?"
    )
    parser.add_argument(
        "--self-test",
        action="store_true"
    )

    args = parser.parse_args()

    try:
        if args.self_test:
            self_test()

        elif args.json_file and args.lean_file:
            raw = Path(
                args.json_file
            ).read_bytes()

            lean = Path(
                args.lean_file
            ).read_text(encoding="utf-8")

            audit(raw, lean)

            print(
                "P39_DATA_PRESERVATION_PASS"
            )

        else:
            parser.error(
                "provide JSON and Lean paths, "
                "or --self-test"
            )

    except (
        AuditError,
        OSError,
        UnicodeError
    ) as exc:
        print(
            "P39_AUDIT_FAIL: " + str(exc),
            file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
