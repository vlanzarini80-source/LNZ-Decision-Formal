
#!/usr/bin/env python3
"""Generate paired JSON/Lean instances and reject mutated inputs."""
import copy
import json
from pathlib import Path

from lnz_p34d import process, Rejected

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "p35_generated"

BASE = {
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


def encoded(d):
    return json.dumps(
        d, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def variant(name, lo, hi, coeff, witness, threshold, objective):
    d = copy.deepcopy(BASE)
    d["case_id"] = name
    n = len(lo)
    d["problem"].update(
        dimension=n, lo=lo, hi=hi, coeff=coeff
    )
    d["certificate"].update(
        witness=witness,
        threshold=threshold,
        objective=objective
    )
    return d


CASES = [
    variant("one", ["0"], ["1"], ["7"], ["1"], "7", "7"),
    variant("two", ["0", "0"], ["1", "1"],
            ["1", "2"], ["1", "0"], "1", "1"),
    variant("three", ["0", "0", "0"], ["1", "1", "1"],
            ["1", "2", "3"], ["1", "0", "0"], "1", "1"),
    variant("four", ["0", "0", "0", "0"],
            ["1", "1", "1", "1"], ["1", "2", "3", "4"],
            ["1", "0", "0", "0"], "1", "1"),
    variant("interior", ["0", "0"], ["1", "1"],
            ["1", "1"], ["0.5", "0.5"], "1", "1"),
    variant("fixed", ["1", "0"], ["1", "0"],
            ["9", "-3"], ["1", "0"], "0", "9"),
    variant("rational", ["0", "0"], ["1", "1"],
            ["0.125", "0.25"], ["1", "0"],
            "0.125", "0.125")
]


def main():
    OUT.mkdir(exist_ok=True)
    paths = []
    json_paths = []

    for case in CASES:
        raw = encoded(case)
        result = process(raw)

        if result["verification"] != "VALID":
            raise AssertionError(
                f"valid case rejected: {case['case_id']}"
            )

        name = case["case_id"]
        json_path = OUT / f"P35_{name}.json"
        lean_path = OUT / f"P35_{name}.lean"

        # Preserve exactly the bytes supplied to process().
        json_path.write_bytes(raw)
        lean_path.write_text(
            result["lean_source"], encoding="utf-8"
        )

        paths.append(str(lean_path.relative_to(ROOT)))
        json_paths.append(str(json_path.relative_to(ROOT)))

    invalid = []

    for key, val in [
        ("objective", "999"),
        ("threshold", "-9"),
        ("witness", ["0", "1"])
    ]:
        d = copy.deepcopy(BASE)
        d["certificate"][key] = val
        invalid.append((key, d))

    d = copy.deepcopy(BASE)
    d["problem"]["hi"] = ["0", "1"]
    invalid.append(("bound", d))

    for name, d in invalid:
        try:
            process(encoded(d))
        except Rejected:
            pass
        else:
            raise AssertionError(
                f"invalid accepted: {name}"
            )

    print(json.dumps({
        "python_generated": paths,
        "json_inputs": json_paths,
        "python_rejected_mutations": [
            name for name, _ in invalid
        ],
        "lean_compiled": False
    }, indent=2))


if __name__ == "__main__":
    main()
