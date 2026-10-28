
import copy
import json
import unittest

from p38_independent import (
    AuditError,
    audit,
    expected_source,
    validate
)

BASE = {
    'schema_version': 'PENSAI-LNZ-POC-0.2',
    'case_id': 'T0',
    'problem': {
        'type': 'box_simplex_min',
        'dimension': 2,
        'lo': ['0', '0'],
        'hi': ['1', '1'],
        'coeff': ['1', '2']
    },
    'certificate': {
        'witness': ['1', '0'],
        'threshold': '1',
        'objective': '1'
    },
    'evidence': {
        'complete': True,
        'noncompensatory_violation': False
    }
}

def raw(x):
    return json.dumps(
        x, separators=(',', ':')
    ).encode()

class Tests(unittest.TestCase):
    def setUp(self):
        self.doc = copy.deepcopy(BASE)
        self.src = expected_source(validate(raw(self.doc)))

    def test_baseline(self):
        self.assertEqual(
            audit(raw(self.doc), self.src)['result'],
            'P38A_PASS'
        )

    def test_all_six_fields_tampered(self):
        replacements = [
            'BoxCertificate 2',
            'lo :=',
            'hi :=',
            'coeff :=',
            'witness :=',
            'threshold :=',
            'objective :='
        ]

        for s in replacements:
            with self.subTest(field=s):
                self.assertRaises(
                    AuditError,
                    audit,
                    raw(self.doc),
                    self.src.replace(s, s + ' ', 1)
                )

    def test_mathematically_valid_but_mismatched(self):
        alt = copy.deepcopy(self.doc)
        alt['problem']['coeff'] = ['1', '3']

        self.assertRaises(
            AuditError,
            audit,
            raw(self.doc),
            expected_source(validate(raw(alt)))
        )

    def test_bad_objective(self):
        self.doc['certificate']['objective'] = '2'
        self.assertRaises(
            AuditError, audit, raw(self.doc), self.src
        )

    def test_bad_exchange(self):
        self.doc['certificate']['threshold'] = '-1'
        self.assertRaises(
            AuditError, audit, raw(self.doc), self.src
        )

    def test_duplicate_keys(self):
        duplicate = raw(self.doc).replace(
            b'"case_id":"T0",',
            b'"case_id":"T0","case_id":"T0",'
        )
        self.assertRaises(
            AuditError, validate, duplicate
        )

    def test_fixed_coordinates(self):
        d = copy.deepcopy(BASE)

        d['problem'].update(
            lo=['1', '0'],
            hi=['1', '0'],
            coeff=['9', '-3']
        )
        d['certificate'].update(
            witness=['1', '0'],
            threshold='0',
            objective='9'
        )

        v = validate(raw(d))
        self.assertEqual(
            audit(raw(d), expected_source(v))['result'],
            'P38A_PASS'
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
