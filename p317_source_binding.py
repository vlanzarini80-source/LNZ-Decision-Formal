
#!/usr/bin/env python3
"""P3.17a: exact JSON-to-Lean source and input binding.

Scope:
- deterministic Lean source identity;
- independent JSON-to-Lean data audit;
- explicit SHA256 input identity;
- adversarial mutation rejection.

Does not prove semantic correctness of Lean elaboration.
"""

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from lnz_p34d import process, Rejected
from p310a_audit import audit, AuditError
from test_p311_independent import baseline


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_binding(
    raw: bytes,
    candidate: bytes,
    expected_input_sha256: str,
) -> dict:
    """Check input identity and exact generated source."""

    if not isinstance(raw, bytes):
        raise AssertionError("INVALID_INPUT_TYPE")

    if not isinstance(candidate, bytes):
        raise AssertionError("INVALID_SOURCE_TYPE")

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        expected_input_sha256,
    ):
        raise AssertionError("INVALID_EXPECTED_DIGEST")

    actual_input_sha256 = sha256(raw)

    if actual_input_sha256 != expected_input_sha256:
        raise AssertionError("INPUT_IDENTITY_MISMATCH")

    result = process(raw)

    if result["sha256_input"] != actual_input_sha256:
        raise AssertionError("GENERATOR_DIGEST_MISMATCH")

    expected_source = result["lean_source"].encode(
        "utf-8"
    )

    if candidate != expected_source:
        raise AssertionError(
            "SOURCE_NOT_GENERATOR_IDENTICAL"
        )

    if audit(
        raw,
        candidate.decode("utf-8"),
    ) is not True:
        raise AssertionError("DATA_AUDIT_FAILED")

    return {
        "input_sha256": actual_input_sha256,
        "source_sha256": sha256(candidate),
    }


def must_reject(
    label: str,
    raw: bytes,
    source: bytes,
    trusted_input_sha256: str,
):
    """A mutant must be rejected by the binding check."""

    try:
        check_binding(
            raw,
            source,
            trusted_input_sha256,
        )
    except (
        AssertionError,
        Rejected,
        AuditError,
        ValueError,
        UnicodeError,
    ):
        print("P317_MUTANT_REJECTED:", label)
        return

    raise AssertionError(
        "MUTANT_ACCEPTED: " + label
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        help="Original JSON input file",
    )

    parser.add_argument(
        "--source",
        help="Candidate Lean source file",
    )

    parser.add_argument(
        "--expected-input-sha256",
        help=(
            "Trusted SHA256 of the original JSON bytes. "
            "Required for external input."
        ),
    )

    parser.add_argument(
        "--report",
        default="p317_binding_report.json",
    )

    args = parser.parse_args()

    if args.input:
        if not args.expected_input_sha256:
            parser.error(
                "--expected-input-sha256 is required "
                "with --input"
            )

        raw = Path(args.input).read_bytes()

        trusted_input_sha256 = (
            args.expected_input_sha256
        )

        input_mode = "external_digest_supplied"

    else:
        if args.expected_input_sha256:
            parser.error(
                "Expected digest requires --input"
            )

        raw = json.dumps(
            baseline(),
            separators=(",", ":"),
        ).encode("utf-8")

        trusted_input_sha256 = sha256(raw)

        input_mode = "internal_test_fixture"

    original = process(raw)["lean_source"].encode(
        "utf-8"
    )

    if args.source:
        candidate = Path(args.source).read_bytes()
    else:
        candidate = original

    report = check_binding(
        raw,
        candidate,
        trusted_input_sha256,
    )

    print("P317_EXACT_SOURCE_BINDING_PASS")

    text = original.decode("utf-8")

    # Mutations affect the actual generated source.
    # No expected mathematical result is injected.

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
                "(v : Fin 1 → ℚ)\n"
                "    -- (v : Fin ",
                1,
            ),

        "appended_source":
            text + "\n-- unexpected appended source\n",
    }

    rejected = 0

    for label, changed in mutations.items():
        if changed == text:
            raise AssertionError(
                "MUTATION_NOT_APPLIED: " + label
            )

        must_reject(
            label,
            raw,
            changed.encode("utf-8"),
            trusted_input_sha256,
        )

        rejected += 1

    # Change only the case identity, preserving
    # all mathematical fields.

    changed_doc = copy.deepcopy(
        json.loads(raw)
    )

    original_case_id = changed_doc["case_id"]

    changed_doc["case_id"] = (
        "P317_DIFFERENT_CASE"
        if original_case_id != "P317_DIFFERENT_CASE"
        else "P317_ANOTHER_CASE"
    )

    changed_raw = json.dumps(
        changed_doc,
        separators=(",", ":"),
    ).encode("utf-8")

    if changed_raw == raw:
        raise AssertionError(
            "JSON_MUTATION_NOT_APPLIED"
        )

    if sha256(changed_raw) == trusted_input_sha256:
        raise AssertionError(
            "UNEXPECTED_DIGEST_COLLISION"
        )

    must_reject(
        "changed_case_identity",
        changed_raw,
        original,
        trusted_input_sha256,
    )

    rejected += 1

    if rejected != 11:
        raise AssertionError(
            "UNEXPECTED_MUTATION_COUNT"
        )

    report.update({
        "mutation_rejections": rejected,
        "input_mode": input_mode,
        "scope": (
            "Exact generated-source identity, "
            "independent data audit, and input "
            "digest binding. Does not establish "
            "Lean elaborated-term semantics."
        ),
    })

    Path(args.report).write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "P317_SOURCE_BINDING_CANDIDATE_PASS"
    )


if __name__ == "__main__":
    main()
