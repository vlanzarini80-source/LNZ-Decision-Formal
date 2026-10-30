
#!/usr/bin/env python3
"""P3.10a: strict JSON-to-Lean data audit.

Supports compact and multiline Lean certificates.
Does not prove Lean semantics or generator provenance.
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

Q = (
    r"\(\s*\(\s*(-?\d+)\s*:\s*ℚ\s*\)"
    r"\s*/\s*\(\s*(\d+)\s*:\s*ℚ\s*\)\s*\)"
)

RATIONAL = re.compile(Q)

HEADER = re.compile(
    r"private\s+def\s+p34Cert\s*:\s*"
    r"BoxCertificate\s+(\d+)\s*:=\s*\{"
)

VECTOR = re.compile(
    r"\(?\s*fun\s+i\s*:\s*Fin\s+(\d+)"
    r"\s*=>\s*\(\s*#\[\s*(.*?)\s*\]"
    r"\s*\)\s*\[\s*i\s*\]\s*\)?\Z",
    re.S
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


def require_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != expected:
        raise AuditError("wrong keys: " + label)


def decimal_exact(s):
    if not isinstance(s, str) or not DECIMAL.fullmatch(s):
        raise AuditError("invalid decimal")

    if len(s.lstrip("-").replace(".", "")) > 80:
        raise AuditError("oversized decimal")

    if s.startswith("-") and set(s[1:]) <= {"0", "."}:
        raise AuditError("negative zero")

    if "." in s and s.endswith("0"):
        raise AuditError("noncanonical decimal")

    return Fraction(s)


def parse_json(raw):
    if len(raw) > 1_000_000:
        raise AuditError("oversized input")

    try:
        doc = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (
                _ for _ in ()
            ).throw(AuditError("nonfinite"))
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError("invalid JSON") from exc

    require_keys(doc, ROOT, "root")

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

    require_keys(p, PROBLEM, "problem")
    require_keys(c, CERT, "certificate")
    require_keys(e, EVIDENCE, "evidence")

    if p["type"] != "box_simplex_min":
        raise AuditError("problem type")

    n = p["dimension"]

    if type(n) is not int or not 1 <= n <= 200:
        raise AuditError("dimension")

    result = {"dimension": n}

    for field in FIELDS:
        source = c if field == "witness" else p

        if (
            not isinstance(source[field], list)
            or len(source[field]) != n
        ):
            raise AuditError("vector length: " + field)

        result[field] = [
            decimal_exact(v)
            for v in source[field]
        ]

    for field in ("threshold", "objective"):
        result[field] = decimal_exact(c[field])

    if any(
        type(e[field]) is not bool
        for field in EVIDENCE
    ):
        raise AuditError("evidence flags")

    return result


def parse_rational(source):
    match = RATIONAL.fullmatch(source.strip())

    if not match:
        raise AuditError("invalid Lean rational")

    numerator, denominator = map(int, match.groups())

    if denominator <= 0:
        raise AuditError("nonpositive denominator")

    return Fraction(numerator, denominator)


def parse_vector(source, n):
    match = VECTOR.fullmatch(source.strip())

    if not match or int(match.group(1)) != n:
        raise AuditError(
            "invalid vector syntax or dimension"
        )

    payload = match.group(2)
    values = []
    pos = 0

    while pos < len(payload):
        while (
            pos < len(payload)
            and payload[pos].isspace()
        ):
            pos += 1

        if pos == len(payload):
            break

        item = RATIONAL.match(payload, pos)

        if not item:
            raise AuditError("invalid vector item")

        values.append(parse_rational(item.group()))
        pos = item.end()

        while (
            pos < len(payload)
            and payload[pos].isspace()
        ):
            pos += 1

        if pos < len(payload):
            if payload[pos] != ",":
                raise AuditError("invalid vector separator")

            pos += 1

            if not payload[pos:].strip():
                raise AuditError("trailing vector comma")

    if len(values) != n:
        raise AuditError("Lean vector length mismatch")

    return values


def parse_lean(source):
    if len(source) > 2_000_000:
        raise AuditError("oversized Lean source")

    headers = list(HEADER.finditer(source))

    if len(headers) != 1:
        raise AuditError(
            "expected exactly one p34Cert definition"
        )

    header = headers[0]
    n = int(header.group(1))

    end = source.find("\n}", header.end())

    if end < 0:
        raise AuditError("unclosed certificate")

    block = source[header.end():end]

    starts = list(
        re.finditer(
            r"(?m)^\s{2}"
            r"(lo|hi|coeff|witness|threshold|objective)"
            r"\s*:=",
            block
        )
    )

    if (
        len(starts) != 6
        or block[:starts[0].start()].strip()
    ):
        raise AuditError(
            "unexpected certificate content or field count"
        )

    result = {"dimension": n}

    for index, match in enumerate(starts):
        field = match.group(1)

        if field in result:
            raise AuditError("duplicate field: " + field)

        next_start = (
            starts[index + 1].start()
            if index + 1 < len(starts)
            else len(block)
        )

        value = block[
            match.end():next_start
        ].strip()

        if value.endswith(","):
            value = value[:-1].rstrip()

        if field in FIELDS:
            result[field] = parse_vector(value, n)
        else:
            result[field] = parse_rational(value)

    expected = {
        "dimension",
        *FIELDS,
        "threshold",
        "objective"
    }

    if set(result) != expected:
        raise AuditError("missing certificate fields")

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
        if expected[field] != observed[field]:
            raise AuditError(
                "semantic mismatch: " + field
            )

    return True


def sample():
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

    compact = """import LNZCertificatePayloadP33
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

    multiline = """import LNZCertificatePayloadP33
namespace LNZ
private def p34Cert : BoxCertificate 2 := {
  lo := fun i : Fin 2 =>
    (#[((0 : ℚ) / (1 : ℚ)),
       ((0 : ℚ) / (1 : ℚ))])[i]
  hi := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((1 : ℚ) / (1 : ℚ))])[i]
  coeff := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((2 : ℚ) / (1 : ℚ))])[i]
  witness := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((0 : ℚ) / (1 : ℚ))])[i]
  threshold := ((1 : ℚ) / (1 : ℚ))
  objective := ((1 : ℚ) / (1 : ℚ))
}
"""

    return raw, compact, multiline


def self_test():
    raw, compact, multiline = sample()

    audit(raw, compact)
    audit(raw, multiline)

    changes = [
        multiline.replace(
            "((2 : ℚ)", "((3 : ℚ)"
        ),
        multiline.replace(
            "BoxCertificate 2",
            "BoxCertificate 3"
        ),
        multiline.replace(
            "threshold := ((1 : ℚ)",
            "threshold := ((2 : ℚ)"
        ),
        multiline.replace(
            "witness :=",
            "unknown :="
        ),
        multiline.replace(
            "objective := ((1 : ℚ)",
            "objective := ((2 : ℚ)"
        ),
        multiline.replace(
            "hi := fun",
            "lo := fun"
        )
    ]

    for index, changed in enumerate(changes, 1):
        try:
            audit(raw, changed)
        except AuditError:
            continue

        raise AssertionError(
            f"mutation {index} incorrectly accepted"
        )

    print(
        "P310A_SELF_TEST_PASS: "
        "2 formats accepted, 6 mutations rejected"
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
        if (
            args.self_test
            and not args.json_file
            and not args.lean_file
        ):
            self_test()

        elif (
            not args.self_test
            and args.json_file
            and args.lean_file
        ):
            raw = Path(
                args.json_file
            ).read_bytes()

            lean = Path(
                args.lean_file
            ).read_text(encoding="utf-8")

            audit(raw, lean)

            print("P310A_DATA_PRESERVATION_PASS")

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
            "P310A_AUDIT_FAIL: " + str(exc),
            file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
