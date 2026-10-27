
#!/usr/bin/env python3
"""Experimental PENSAI-LNZ 0.2 bridge. Independent of proprietary PENSAI code."""
import argparse
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

VERSION = 'PENSAI-LNZ-POC-0.2'
DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z')
ROOT = {'schema_version', 'case_id', 'problem', 'certificate', 'evidence'}
PROBLEM = {'type', 'dimension', 'lo', 'hi', 'coeff'}
CERT = {'witness', 'threshold', 'objective'}
EVIDENCE = {'complete', 'noncompensatory_violation'}

class Rejected(ValueError):
    pass

def pairs_no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise Rejected('duplicate_key:' + k)
        result[k] = v
    return result

def rational(s):
    if not isinstance(s, str) or not DECIMAL.fullmatch(s):
        raise Rejected('invalid_decimal')
    if len(s.lstrip('-').replace('.', '')) > 80 or (s.startswith('-') and Fraction(s) == 0):
        raise Rejected('noncanonical_or_oversized_decimal')
    if '.' in s and (s.endswith('0') or s.endswith('.')):
        raise Rejected('noncanonical_decimal')
    return Fraction(s)

def exact_keys(obj, keys, where):
    if not isinstance(obj, dict) or set(obj) != keys:
        raise Rejected('schema_keys:' + where)

def load_and_validate(raw):
    if len(raw) > 1_000_000:
        raise Rejected('oversized_input')
    try:
        doc = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs_no_duplicates,
                         parse_constant=lambda _: (_ for _ in ()).throw(Rejected('nonfinite')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Rejected('invalid_json') from exc
    exact_keys(doc, ROOT, 'root')
    if doc['schema_version'] != VERSION:
        raise Rejected('schema_version')
    if not isinstance(doc['case_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', doc['case_id']):
        raise Rejected('case_id')
    p, c, e = doc['problem'], doc['certificate'], doc['evidence']
    exact_keys(p, PROBLEM, 'problem')
    exact_keys(c, CERT, 'certificate')
    exact_keys(e, EVIDENCE, 'evidence')
    if p['type'] != 'box_simplex_min':
        raise Rejected('problem_type')
    n = p['dimension']
    if type(n) is not int or not 1 <= n <= 200:
        raise Rejected('dimension')
    values = {}
    for key in ('lo', 'hi', 'coeff'):
        if not isinstance(p[key], list) or len(p[key]) != n:
            raise Rejected('vector_length:' + key)
        values[key] = [rational(v) for v in p[key]]
    if not isinstance(c['witness'], list) or len(c['witness']) != n:
        raise Rejected('vector_length:witness')
    values['witness'] = [rational(v) for v in c['witness']]
    values['threshold'] = rational(c['threshold'])
    values['objective'] = rational(c['objective'])
    if any(type(e[k]) is not bool for k in EVIDENCE):
        raise Rejected('evidence_boolean')
    return doc, values

def verify(values):
    lo, hi, coeff, w = (values[k] for k in ('lo', 'hi', 'coeff', 'witness'))
    lam, obj = values['threshold'], values['objective']
    for i, (a, b, x, c) in enumerate(zip(lo, hi, w, coeff)):
        if not (0 <= a <= x <= b <= 1):
            raise Rejected(f'bounds:{i}')
        if a < x and not c <= lam:
            raise Rejected(f'exchange_left:{i}')
        if x < b and not lam <= c:
            raise Rejected(f'exchange_right:{i}')
    if sum(w, Fraction(0)) != 1:
        raise Rejected('simplex_sum')
    if sum((a*b for a, b in zip(coeff, w)), Fraction(0)) != obj:
        raise Rejected('objective_mismatch')

def lean_q(q):
    return f'(({q.numerator} : ℚ) / ({q.denominator} : ℚ))'

def lean_vec(xs, n):
    return '(fun i : Fin ' + str(n) + ' => (#[ ' + ', '.join(lean_q(v) for v in xs) + ' ])[i])'

def generate(values):
    n = len(values['lo'])
    fields = ['lo', 'hi', 'coeff', 'witness']
    body = ['import LNZCertificatePayloadP33', '', 'namespace LNZ', '',
            f'private def p34Cert : BoxCertificate {n} := {{']
    body += [f'  {k} := {lean_vec(values[k], n)}' + (',' if k != 'witness' else ',') for k in fields]
    body += [f'  threshold := {lean_q(values["threshold"])},',
             f'  objective := {lean_q(values["objective"])}', '}', '',
             'private theorem p34Valid : ValidBoxCertificate p34Cert := by',
             '  unfold ValidBoxCertificate', '  constructor',
             '  · intro i', '    fin_cases i <;> norm_num [p34Cert]',
             '  constructor', '  · norm_num [p34Cert, Fin.sum_univ_succ]',
             '  constructor', '  · norm_num [p34Cert, Fin.sum_univ_succ]',
             '  constructor', '  · intro i _',
             '    fin_cases i <;> norm_num [p34Cert] at *',
             '  · intro i _',
             '    fin_cases i <;> norm_num [p34Cert] at *', '',
             'theorem p34_instance_optimal',
             f'    (v : Fin {n} → ℚ)',
             '    (hvlo : ∀ i, p34Cert.lo i ≤ v i)',
             '    (hvhi : ∀ i, v i ≤ p34Cert.hi i)',
             '    (hvsum : ∑ i, v i = 1) :',
             '    p34Cert.objective ≤ ∑ i, p34Cert.coeff i * v i := by',
             '  exact valid_box_certificate_optimal p34Cert p34Valid v hvlo hvhi hvsum',
             '', '#print axioms LNZ.p34_instance_optimal', '', 'end LNZ', '']
    return '\n'.join(body)

def process(raw):
    doc, values = load_and_validate(raw)
    verify(values)
    decision = ('STOP' if doc['evidence']['noncompensatory_violation']
                else 'HOLD' if not doc['evidence']['complete'] else 'ALLOW')
    return {'verification': 'VALID', 'illustrative_policy': decision,
            'sha256_input': hashlib.sha256(raw).hexdigest(),
            'lean_source': generate(values)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json_file')
    ap.add_argument('--lean-out', default='P34Generated.lean')
    args = ap.parse_args()
    raw = Path(args.json_file).read_bytes()
    try:
        result = process(raw)
    except Rejected as exc:
        print(json.dumps({'verification': 'INVALID', 'reason': str(exc)}, indent=2))
        return 1
    Path(args.lean_out).write_text(result.pop('lean_source'), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
