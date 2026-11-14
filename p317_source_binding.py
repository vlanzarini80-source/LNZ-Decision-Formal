
#!/usr/bin/env python3
"""P3.17a: exact JSON-to-Lean source binding.

Checks deterministic source identity and independent data
audit. Does NOT prove the Python translator correct or
verify the elaborated Lean theorem.
"""

import argparse
import hashlib
import json
from pathlib import Path

from lnz_p34d import process
from p310a_audit import audit
from test_p311_independent import baseline


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_binding(raw: bytes, candidate: bytes) -> dict:
    """Require exact identity with freshly generated Lean."""
    result = process(raw)
    expected = result["lean_source"].encode("utf-8")

    if result["sha256_input"] != sha256(raw):
        raise AssertionError("INPUT_DIGEST_MISMATCH")

    if not isinstance(candidate, bytes):
        raise AssertionError("INVALID_SOURCE_TYPE")

    if candidate != expected:
        raise AssertionError("SOURCE_NOT_GENERATOR_IDENTICAL")

    if audit(raw, candidate.decode("utf-8")) is not True:
        raise AssertionError("DATA_AUDIT_FAILED")

    return {
        "input_sha256": sha256(raw),
        "source_sha256": sha256(candidate),
    }


def must_reject(label: str, raw: bytes, source: bytes):
    try:
        check_binding(raw, source)
    except (AssertionError, ValueError, UnicodeError):
        print("P317_MUTANT_REJECTED:", label)
        return

    raise AssertionError("MUTANT_ACCEPTED: " + label)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--source")
    parser.add_argument(
        "--report",
        default="p317_binding_report.json",
    )
    args = parser.parse_args()

    if args.input:
        raw = Path(args.input).read_bytes()
    else:
        raw = json.dumps(
            baseline(),
            separators=(",", ":"),
        ).encode("utf-8")

    original = process(raw)["lean_source"].encode("utf-8")

    if args.source:
        candidate = Path(args.source).read_bytes()
    else:
        candidate = original

    report = check_binding(raw, candidate)
    print("P317_EXACT_SOURCE_BINDING_PASS")

    text = original.decode("utf-8")

    # All mutations are derived from actual generated
    # source. No target mathematical result is injected.
    mutations = {
        "coefficient":
            text.replace(
                "  coeff :=",
                "  coeff := (fun _ => (0 : ℚ)),\n"
                "  -- coeff :=",
                1,
            ),
        "lower_bound":
            text.replace(
                "  lo :=",
                "  lo := (fun _ => (0 : ℚ)),\n"
                "  -- lo :=",
                1,
            ),
        "upper_bound":
            text.replace(
                "  hi :=",
                "  hi := (fun _ => (0 : ℚ)),\n"
                "  -- hi :=",
                1,
            ),
        "witness":
            text.replace(
                "  witness :=",
                "  witness := (fun _ => (0 : ℚ)),\n"
                "  -- witness :=",
                1,
            ),
        "threshold":
            text.replace(
                "  threshold :=",
                "  threshold := ((0 : ℚ) / (1 : ℚ)),\n"
                "  -- threshold :=",
                1,
            ),
        "objective":
            text.replace(
                "  objective :=",
                "  objective := ((0 : ℚ) / (1 : ℚ))\n"
                "  -- objective :=",
                1,
            ),
        "dimension":
            text.replace(
                "BoxCertificate ",
                "BoxCertificate 1 -- ",
                1,
            ),
        "theorem_name":
            text.replace(
                "theorem p34_instance_optimal",
                "theorem p34_instance_altered",
                1,
            ),
        "theorem_binder":
            text.replace(
                "(v : Fin ",
                "(v : Fin 1 → ℚ)\n    -- (v : Fin ",
                1,
            ),
        "appended_source":
            text + "\n-- unexpected appended source\n",
    }

    for label, changed in mutations.items():
        if changed == text:
            raise AssertionError(
                "MUTATION_NOT_APPLIED: " + label
            )
        must_reject(
            label,
            raw,
            changed.encode("utf-8"),
        )

    changed_doc = json.loads(raw)
    changed_doc["case_id"] = "P317_DIFFERENT_CASE"

    changed_raw = json.dumps(
        changed_doc,
        separators=(",", ":"),
    ).encode("utf-8")

    if changed_raw == raw:
        raise AssertionError("JSON_MUTATION_NOT_APPLIED")

    must_reject(
        "changed_case_identity",
        changed_raw,
        original,
    )

    report.update({
        "mutation_rejections": len(mutations) + 1,
        "scope": (
            "Exact generated-source identity and "
            "JSON-to-Lean data audit. "
            "Not an elaborated-term proof."
        ),
    })

    Path(args.report).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("P317_SOURCE_BINDING_CANDIDATE_PASS")


if __name__ == "__main__":
    main()
