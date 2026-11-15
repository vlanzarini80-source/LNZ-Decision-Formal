
#!/usr/bin/env python3
"""P320.3: two independent Lean-certified structured instances and an external anchor.

This is a CI evidence audit, not a proof of natural-language equivalence.
The trusted SHA256 must be supplied outside the candidate bundle.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from lnz_p34d import process
from p320_source_contract import canonical

HEX = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def document(coeff, witness, threshold, case_id):
    return {
        "schema_version": "PENSAI-LNZ-POC-0.2",
        "case_id": case_id,
        "problem": {
            "type": "box_simplex_min", "dimension": 3,
            "lo": ["0", "0", "0"], "hi": ["1", "1", "1"],
            "coeff": coeff,
        },
        "certificate": {
            "witness": witness, "threshold": threshold,
            "objective": "1",
        },
        "evidence": {
            "complete": True, "noncompensatory_violation": False,
        },
    }


def fixtures(root):
    # These are input cases, NOT expected results inserted into a verifier.
    cases = {
        "A": document(["1", "2", "3"], ["1", "0", "0"], "1", "P3203_A"),
        "B": document(["2", "1", "3"], ["0", "1", "0"], "1", "P3203_B"),
    }
    root.mkdir(parents=True, exist_ok=True)
    for label, doc in cases.items():
        folder = root / label
        folder.mkdir(parents=True, exist_ok=True)
        raw = canonical(doc)
        # Fail immediately if either mathematical certificate is invalid.
        process(raw)
        (folder / "source.json").write_bytes(raw)
        (folder / "formal.json").write_bytes(raw)
    print("FIXTURE_A_SHA256=" + digest((root / "A/source.json").read_bytes()))
    print("FIXTURE_B_SHA256=" + digest((root / "B/source.json").read_bytes()))


def inspect(root, trusted_sha):
    require(bool(HEX.fullmatch(trusted_sha)), "TRUSTED_ANCHOR_REQUIRED")
    a, b = root / "A", root / "B"
    a_source = (a / "source.json").read_bytes()
    b_source = (b / "source.json").read_bytes()
    require(digest(a_source) == trusted_sha, "ORIGINAL_ANCHOR_MISMATCH")
    require(a_source != b_source, "INSTANCES_NOT_DISTINCT")

    from p3202_bound_lean import check
    previous = Path.cwd()
    results = {}
    try:
        for label, folder in (("A", a), ("B", b)):
            os.chdir(folder.resolve())
            result = check("source.json", "formal.json", "positive.log", "exit.txt")
            require(result["status"] == "BOUND_AND_FORMALLY_PROVED", "NOT_PROVED:" + label)
            results[label] = result
            os.chdir(previous)
    finally:
        os.chdir(previous)

    require(
        results["A"]["lean_source_sha256"] != results["B"]["lean_source_sha256"],
        "PROOFS_NOT_DISTINCT",
    )
    return results


def reject(label, fn, expected):
    try:
        fn()
    except (ValueError, KeyError) as exc:
        reason = str(exc)
        require(expected in reason, "WRONG_REJECTION_CAUSE:" + label + ":" + reason)
        print("REJECTED:" + label + ":" + reason)
        return
    raise AssertionError("ATTACK_ACCEPTED:" + label)


def audit(root, trusted_sha):
    baseline = inspect(root, trusted_sha)
    from p3202_bound_lean import check
    a, b = root / "A", root / "B"
    original = Path.cwd()

    # Swap a real, successfully compiled B proof into A's bundle.
    a_lean = (a / "P3202Generated.lean").read_bytes()
    b_lean = (b / "P3202Generated.lean").read_bytes()
    require(a_lean != b_lean, "SAME_LEAN_SOURCE")

    try:
        (a / "P3202Generated.lean").write_bytes(b_lean)

        def swapped():
            os.chdir(a.resolve())
            try:
                check("source.json", "formal.json", "positive.log", "exit.txt")
            finally:
                os.chdir(original)

        reject("PROOF_B_AS_A", swapped, "LEAN_SOURCE_MISMATCH")
    finally:
        (a / "P3202Generated.lean").write_bytes(a_lean)
        os.chdir(original)

    # Full coordinated substitution of A with B.
    names = (
        "source.json", "formal.json", "p3202-contract.json",
        "p3202-manifest.json", "P3202Generated.lean",
        "positive.log", "exit.txt",
    )
    saved = {name: (a / name).read_bytes() for name in names}

    try:
        for name in names:
            (a / name).write_bytes((b / name).read_bytes())

        reject(
            "FULL_COORDINATED_REPLACEMENT",
            lambda: inspect(root, trusted_sha),
            "ORIGINAL_ANCHOR_MISMATCH",
        )
    finally:
        for name, data in saved.items():
            (a / name).write_bytes(data)

    report = {
        "status": "P3203_AUDIT_PASS",
        "anchor_sha256": trusted_sha,
        "A_lean_sha256": baseline["A"]["lean_source_sha256"],
        "B_lean_sha256": baseline["B"]["lean_source_sha256"],
        "natural_language_equivalence": False,
        "trusted_anchor_external": True,
    }
    (root / "audit-report.json").write_bytes(canonical(report) + b"\n")
    print(json.dumps(report, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["fixtures", "audit"])
    p.add_argument("--root", default="p3203-evidence")
    p.add_argument("--trusted-sha256")
    args = p.parse_args()

    root = Path(args.root).resolve()
    if args.command == "fixtures":
        fixtures(root)
    else:
        audit(root, args.trusted_sha256 or "")


if __name__ == "__main__":
    main()
