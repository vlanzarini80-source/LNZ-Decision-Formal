
#!/usr/bin/env python3
"""P3.11d: independent exact optimality and certificate mutation audit.

Separates primal optimality from threshold-certificate validity.
Does not establish historical JSON provenance or Lean semantic soundness.
"""

import copy
import json
import random
from fractions import Fraction

from lnz_p34d import process, Rejected
from p310a_audit import audit, AuditError


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def encode(doc):
    return json.dumps(
        doc, separators=(",", ":")
    ).encode("utf-8")


def oracle(doc):
    """Independent primal optimality test via feasible improving transfers."""
    p, cert = doc["problem"], doc["certificate"]
    n = p["dimension"]

    lo = list(map(Fraction, p["lo"]))
    hi = list(map(Fraction, p["hi"]))
    coeff = list(map(Fraction, p["coeff"]))
    w = list(map(Fraction, cert["witness"]))
    obj = Fraction(cert["objective"])

    if not all(
        0 <= lo[i] <= w[i] <= hi[i] <= 1
        for i in range(n)
    ):
        return False

    if sum(w, Fraction(0)) != 1:
        return False

    if sum(
        (coeff[i] * w[i] for i in range(n)),
        Fraction(0)
    ) != obj:
        return False

    return not any(
        w[i] > lo[i]
        and w[j] < hi[j]
        and coeff[i] > coeff[j]
        for i in range(n)
        for j in range(n)
    )


def certificate_oracle(doc):
    """Independent exact check of the threshold-based certificate."""
    p, cert = doc["problem"], doc["certificate"]
    n = p["dimension"]

    lo = list(map(Fraction, p["lo"]))
    hi = list(map(Fraction, p["hi"]))
    coeff = list(map(Fraction, p["coeff"]))
    w = list(map(Fraction, cert["witness"]))
    lam = Fraction(cert["threshold"])
    obj = Fraction(cert["objective"])

    if not all(
        0 <= lo[i] <= w[i] <= hi[i] <= 1
        for i in range(n)
    ):
        return False

    if sum(w, Fraction(0)) != 1:
        return False

    if sum(
        (coeff[i] * w[i] for i in range(n)),
        Fraction(0)
    ) != obj:
        return False

    return all(
        (not lo[i] < w[i] or coeff[i] <= lam)
        and (not w[i] < hi[i] or lam <= coeff[i])
        for i in range(n)
    )


def baseline():
    return {
        "schema_version": "PENSAI-LNZ-POC-0.2",
        "case_id": "P311_INDEPENDENT",
        "problem": {
            "type": "box_simplex_min",
            "dimension": 3,
            "lo": ["0", "0", "0"],
            "hi": ["1", "1", "1"],
            "coeff": ["1", "2", "3"]
        },
        "certificate": {
            "witness": ["1", "0", "0"],
            "threshold": "1",
            "objective": "1"
        },
        "evidence": {
            "complete": True,
            "noncompensatory_violation": False
        }
    }


def rejected_by_generator(doc):
    try:
        process(encode(doc))
    except Rejected:
        return True

    return False


def test_baseline():
    doc = baseline()

    require(
        oracle(doc),
        "Primal oracle rejected baseline"
    )

    require(
        certificate_oracle(doc),
        "Certificate oracle rejected baseline"
    )

    result = process(encode(doc))

    require(
        result["verification"] == "VALID",
        "Generator rejected baseline"
    )

    audit(encode(doc), result["lean_source"])

    print("P311_BASELINE_PASS")


def test_numeric_mutations():
    original = baseline()

    original_lean = process(
        encode(original)
    )["lean_source"]

    mutations = [
        ("lo", "problem", "lo", 1, "0.5"),
        ("hi", "problem", "hi", 0, "0.5"),
        ("coeff", "problem", "coeff", 0, "4"),
        ("witness", "certificate", "witness", 0, "0"),
        ("threshold", "certificate", "threshold", None, "0"),
        ("objective", "certificate", "objective", None, "2"),
    ]

    for label, section, field, index, value in mutations:
        doc = copy.deepcopy(original)

        if index is None:
            doc[section][field] = value
        else:
            doc[section][field][index] = value

        require(
            not certificate_oracle(doc),
            "Mutation remains certificate-valid: " + label
        )

        if label == "threshold":
            require(
                oracle(doc),
                "Threshold mutation changed primal optimality"
            )
        else:
            require(
                not oracle(doc),
                "Mutation remains primal-optimal: " + label
            )

        try:
            audit(encode(doc), original_lean)
        except AuditError:
            pass
        else:
            raise AssertionError(
                "Auditor accepted mutation: " + label
            )

        require(
            rejected_by_generator(doc),
            "Generator accepted invalid certificate: " + label
        )

        print("P311_MUTATION_REJECTED:", label)


def test_suboptimal_certificate():
    doc = baseline()

    doc["certificate"]["witness"] = ["0", "1", "0"]
    doc["certificate"]["objective"] = "2"

    require(
        not oracle(doc),
        "Primal oracle accepted suboptimal witness"
    )

    require(
        not certificate_oracle(doc),
        "Certificate oracle accepted suboptimal witness"
    )

    require(
        rejected_by_generator(doc),
        "Generator accepted suboptimal witness"
    )

    print("P311_SUBOPTIMAL_REJECTED")


def test_randomized():
    rng = random.Random(311)

    for iteration in range(200):
        n = rng.randint(2, 8)
        costs = [
            rng.randint(-10, 10)
            for _ in range(n)
        ]
        selected = rng.randrange(n)

        doc = baseline()
        doc["case_id"] = "P311_RANDOM"
        doc["problem"]["dimension"] = n
        doc["problem"]["lo"] = ["0"] * n
        doc["problem"]["hi"] = ["1"] * n
        doc["problem"]["coeff"] = list(map(str, costs))

        doc["certificate"]["witness"] = [
            "1" if i == selected else "0"
            for i in range(n)
        ]

        doc["certificate"]["objective"] = str(
            costs[selected]
        )
        doc["certificate"]["threshold"] = str(
            costs[selected]
        )

        expected = certificate_oracle(doc)

        require(
            expected == oracle(doc),
            f"Oracle disagreement on randomized case {iteration}"
        )

        try:
            result = process(encode(doc))
            accepted = True
        except Rejected:
            accepted = False

        require(
            accepted == expected,
            f"Generator/certificate oracle disagreement at {iteration}"
        )

        if accepted:
            audit(encode(doc), result["lean_source"])

    print("P311_RANDOMIZED_PASS: 200")


def main():
    test_baseline()
    test_numeric_mutations()
    test_suboptimal_certificate()
    test_randomized()

    print("P311D_INDEPENDENT_AUDIT_PASS")


if __name__ == "__main__":
    main()
