
#!/usr/bin/env python3
"""Generate Lean instances and reject mutated inputs."""
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
        d, ensure_ascii=False, separators=(',', ':')
    ).encode('utf-8')

def variant(name, lo, hi, coeff, witness, threshold, objective):
    d = copy.deepcopy(BASE)
    d['case_id'] = name
    n = len(lo)
    d['problem'].update(
        dimension=n, lo=lo, hi=hi, coeff=coeff
    )
    d['certificate'].update(
        witness=witness,
        threshold=threshold,
        objective=objective
    )
    return d

CASES = [
    variant('one', ['0'], ['1'], ['7'], ['1'], '7', '7'),
    variant('two', ['0', '0'], ['1', '1'],
            ['1', '2'], ['1', '0'], '1', '1'),
    variant('three', ['0', '0', '0'], ['1', '1', '1'],
            ['1', '2', '3'], ['1', '0', '0'], '1', '1'),
    variant('four', ['0', '0', '0', '0'],
            ['1', '1', '1', '1'], ['1', '2', '3', '4'],
            ['1', '0', '0', '0'], '1', '1'),
    variant('interior', ['0', '0'], ['1', '1'],
            ['1', '1'], ['0.5', '0.5'], '1', '1'),
    variant('fixed', ['1', '0'], ['1', '0'],
            ['9', '-3'], ['1', '0'], '0', '9'),
    variant('rational', ['0', '0'], ['1', '1'],
            ['0.125', '0.25'], ['1', '0'],
            '0.125', '0.125')
]

def main():
    OUT.mkdir(exist_ok=True)
    paths = []

    for case in CASES:
        result = process(encoded(case))
        assert result['verification'] == 'VALID'
        name = case['case_id']
        path = OUT / f'P35_{name}.lean'
        path.write_text(
            result['lean_source'], encoding='utf-8'
        )
        paths.append(str(path.relative_to(ROOT)))

    invalid = []
    for key, val in [
        ('objective', '999'),
        ('threshold', '-9'),
        ('witness', ['0', '1'])
    ]:
        d = copy.deepcopy(BASE)
        d['certificate'][key] = val
        invalid.append((key, d))

    d = copy.deepcopy(BASE)
    d['problem']['hi'] = ['0', '1']
    invalid.append(('bound', d))

    for name, d in invalid:
        try:
            process(encoded(d))
        except Rejected:
            pass
        else:
            raise AssertionError(
                f'invalid accepted: {name}'
            )

    print(json.dumps({
        'python_generated': paths,
        'python_rejected_mutations': [
            x[0] for x in invalid
        ],
        'lean_compiled': False
    }, indent=2))

if __name__ == '__main__':
    main()
