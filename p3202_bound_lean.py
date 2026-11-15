
#!/usr/bin/env python3
"""P320.2: bind structured source bytes to Lean evidence.

Not a natural-language semantic equivalence certificate.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from lnz_p34d import process
from p320_source_contract import build, canonical, verify_contract

ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
AXIOMS = re.compile(
    r"'LNZ\.p34_instance_optimal' depends on axioms:"
    r"\s*\[([^\]]*)\]"
)


def require(ok, code):
    if not ok:
        raise ValueError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return Path(path).read_bytes()


def write_json(path, obj):
    Path(path).write_bytes(canonical(obj) + b"\n")


def prepare(source_path, formal_path):
    source, formal = read(source_path), read(formal_path)
    contract = canonical(build(source, formal))
    generated = process(formal)["lean_source"].encode("utf-8")

    bound = verify_contract(
        source, formal, contract, generated
    )
    require(bound["status"] == "BOUND_SYNTACTIC", "NOT_BOUND")

    Path("P3202Generated.lean").write_bytes(generated)
    Path("p3202-contract.json").write_bytes(
        contract + b"\n"
    )

    write_json("p3202-manifest.json", {
        "schema": "LNZ-P320.2-EVIDENCE-1",
        "source_sha256": digest(source),
        "formal_sha256": digest(formal),
        "contract_sha256": digest(contract + b"\n"),
        "lean_sha256": digest(generated),
        "status": "PREPARED_NOT_COMPILED",
        "certified": False,
    })
    print("P3202_PREPARED")


def check(source_path, formal_path, log_path, exit_path):
    source, formal = read(source_path), read(formal_path)
    contract = read("p3202-contract.json")
    lean = read("P3202Generated.lean")
    manifest = json.loads(read("p3202-manifest.json"))

    bound = verify_contract(
        source, formal, contract, lean
    )

    require(
        manifest["schema"] == "LNZ-P320.2-EVIDENCE-1",
        "BAD_SCHEMA",
    )
    require(
        manifest["status"] == "PREPARED_NOT_COMPILED",
        "BAD_MANIFEST_STATUS",
    )
    require(
        manifest["certified"] is False,
        "FALSE_CERTIFICATION",
    )

    for field, data in (
        ("source_sha256", source),
        ("formal_sha256", formal),
        ("contract_sha256", contract),
        ("lean_sha256", lean),
    ):
        require(
            manifest[field] == digest(data),
            "HASH_MISMATCH:" + field,
        )

    require(
        read(exit_path).strip() == b"0",
        "LEAN_EXIT_NONZERO",
    )

    log = read(log_path).decode("utf-8")
    require(
        "error:" not in log and "warning:" not in log,
        "LEAN_DIAGNOSTIC",
    )

    matches = AXIOMS.findall(log)
    require(len(matches) == 1, "AXIOM_REPORT_COUNT")

    names = [s.strip() for s in matches[0].split(",")]
    require(
        len(names) == len(set(names)),
        "DUPLICATE_AXIOM",
    )
    require(
        set(names) == ALLOWED,
        "UNAUTHORIZED_OR_MISSING_AXIOM",
    )

    return {
        "status": "BOUND_AND_FORMALLY_PROVED",
        "source_sha256": digest(source),
        "formal_sha256": digest(formal),
        "lean_source_sha256": digest(lean),
        "lean_axioms": sorted(names),
        "lean_executed": True,
        "document_semantics_certified": False,
        "human_attested": False,
        "certified_arbitrary_documents": False,
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(
        dest="command", required=True
    )

    prep = sub.add_parser("prepare")
    prep.add_argument("source")
    prep.add_argument("formal")

    audit = sub.add_parser("check")
    audit.add_argument("source")
    audit.add_argument("formal")
    audit.add_argument("log")
    audit.add_argument("exit_code")

    args = parser.parse_args()

    try:
        if args.command == "prepare":
            prepare(args.source, args.formal)
        else:
            result = check(
                args.source,
                args.formal,
                args.log,
                args.exit_code,
            )
            write_json("p3202-verdict.json", result)
            print(json.dumps(result, sort_keys=True))
    except (
        ValueError, KeyError, TypeError,
        OSError, UnicodeError
    ) as exc:
        print(json.dumps({
            "status": "UNBOUND",
            "reason": str(exc),
            "certified": False,
        }))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
