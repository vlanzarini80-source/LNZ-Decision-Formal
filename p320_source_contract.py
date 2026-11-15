
#!/usr/bin/env python3
"""P320.1 - Fail-closed structured source/formal binding.

Scope: box_simplex_min JSON documents only.
No natural-language equivalence, signature or Lean execution.
"""

import argparse
import hashlib
import json
from pathlib import Path

from lnz_p34d import load_and_validate, process, Rejected

SCHEMA = "LNZ-P320.1-STRUCTURED-1"
FIELDS = (
    "dimension", "lo", "hi", "coeff",
    "witness", "threshold", "objective",
)


class ContractError(ValueError):
    pass


def fail(code):
    raise ContractError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            fail("DUPLICATE_KEY")
        result[key] = value
    return result


def parse(raw):
    if type(raw) is not bytes:
        fail("INVALID_INPUT_TYPE")
    if len(raw) > 1_000_000:
        fail("OVERSIZED_CONTRACT")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _: fail(
                "NONFINITE_NUMBER"
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("INVALID_JSON") from exc


def exact(obj, keys, where):
    if type(obj) is not dict or set(obj) != set(keys):
        fail("SCHEMA_KEYS_" + where)


def canonical(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def mathematical_claim(doc):
    p = doc["problem"]
    c = doc["certificate"]
    return {
        "dimension": p["dimension"],
        "lo": p["lo"],
        "hi": p["hi"],
        "coeff": p["coeff"],
        "witness": c["witness"],
        "threshold": c["threshold"],
        "objective": c["objective"],
    }


def build(source_bytes, formal_bytes):
    """Bind two separately supplied structured inputs."""

    source_doc, _ = load_and_validate(source_bytes)
    formal_doc, _ = load_and_validate(formal_bytes)

    source_claim = mathematical_claim(source_doc)
    formal_claim = mathematical_claim(formal_doc)

    relation = (
        "SYNTACTIC_MATCH"
        if source_claim == formal_claim
        else "UNESTABLISHED"
    )

    return {
        "schema": SCHEMA,
        "source": {
            "sha256": sha(source_bytes),
            "claim_sha256": sha(
                canonical(source_claim)
            ),
        },
        "formal": {
            "sha256": sha(formal_bytes),
            "claim_sha256": sha(
                canonical(formal_claim)
            ),
        },
        "relation": relation,
        "attestation": None,
    }


def verify_contract(
    source_bytes,
    formal_bytes,
    contract_bytes,
    lean_bytes,
):
    """Recompute the binding and reject every mismatch."""

    if type(lean_bytes) is not bytes:
        fail("LEAN_SOURCE_REQUIRED")

    contract = parse(contract_bytes)

    exact(
        contract,
        (
            "schema", "source", "formal",
            "relation", "attestation",
        ),
        "ROOT",
    )
    exact(
        contract["source"],
        ("sha256", "claim_sha256"),
        "SOURCE",
    )
    exact(
        contract["formal"],
        ("sha256", "claim_sha256"),
        "FORMAL",
    )

    if contract["schema"] != SCHEMA:
        fail("SCHEMA_VERSION")

    if contract["attestation"] is not None:
        fail("UNSUPPORTED_ATTESTATION")

    if contract["relation"] not in (
        "SYNTACTIC_MATCH",
        "UNESTABLISHED",
    ):
        fail("INVALID_RELATION")

    expected = build(source_bytes, formal_bytes)

    if contract != expected:
        fail("CONTRACT_MISMATCH")

    if expected["relation"] != "SYNTACTIC_MATCH":
        fail("CLAIM_MISMATCH")

    # Recompute mathematical validity and generated source.
    formal_result = process(formal_bytes)
    generated = formal_result["lean_source"].encode(
        "utf-8"
    )

    if lean_bytes != generated:
        fail("LEAN_SOURCE_MISMATCH")

    return {
        "status": "BOUND_SYNTACTIC",
        "source_sha256": sha(source_bytes),
        "formal_sha256": sha(formal_bytes),
        "formal_claim_sha256": expected[
            "formal"
        ]["claim_sha256"],
        "lean_source_sha256": sha(generated),
        "lean_executed": False,
        "human_attested": False,
        "document_semantics_certified": False,
        "certified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("formal")
    parser.add_argument("contract")
    parser.add_argument("--lean", required=True)
    args = parser.parse_args()

    try:
        result = verify_contract(
            Path(args.source).read_bytes(),
            Path(args.formal).read_bytes(),
            Path(args.contract).read_bytes(),
            Path(args.lean).read_bytes(),
        )
        print(json.dumps(
            result, sort_keys=True, indent=2
        ))
        return 0

    except (
        ContractError,
        Rejected,
        ValueError,
        TypeError,
        KeyError,
        OSError,
    ) as exc:
        print(json.dumps({
            "status": "UNBOUND",
            "reason": str(exc),
            "certified": False,
        }, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
