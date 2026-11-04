
#!/usr/bin/env python3
"""P3.14-TB-CI candidate: checked JSON/Lean handoff.

Protection model: trusted CI runner, trusted Python/Lean toolchains, and no
untrusted concurrent writer to the private staging directory. Hash checks
are not a defense against an attacker able to mutate files during compiler
execution, compromise the runner or replace dependencies/toolchain.

No general proof of the Python translator is claimed. The original P3.2/P3.3
Lean modules remain unchanged.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from lnz_p34d import process
from p310a_audit import audit
from test_p311_independent import baseline, certificate_oracle


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BoundaryViolation(Exception):
    pass


def check_snapshot(raw: bytes, expected_raw: str, path: Path, expected_lean: str) -> bytes:
    if digest(raw) != expected_raw:
        raise BoundaryViolation('JSON_HASH_MISMATCH')
    current = path.read_bytes()
    if digest(current) != expected_lean:
        raise BoundaryViolation('LEAN_HASH_MISMATCH')
    if not audit(raw, current.decode('utf-8')):
        raise BoundaryViolation('DATA_AUDIT_FAILED')
    return current


def verified_handoff(raw: bytes, path: Path, expected_raw: str,
                     expected_lean: str, runner):
    """Check, invoke compiler, then re-check; fail closed on a mutation.

    In CI, a private staging directory plus trusted runner avoids an untrusted
    concurrent writer. Post-check detects persistent, not transient, mutations.
    """
    check_snapshot(raw, expected_raw, path, expected_lean)
    result = runner(path)
    check_snapshot(raw, expected_raw, path, expected_lean)
    return result


def expect_rejection(name, call):
    try:
        call()
    except BoundaryViolation:
        print('P314_TB_CI_REJECTED:', name)
        return
    raise AssertionError('Manipulation was not rejected: ' + name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lean', action='store_true', help='Run actual lake env lean using compiled dependencies')
    ap.add_argument('--report', default='p314_tb_ci_report.json')
    args = ap.parse_args()

    doc = baseline()
    raw = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    if not certificate_oracle(doc):
        raise AssertionError('Independent baseline oracle rejected input')
    result = process(raw)
    source = result['lean_source'].encode('utf-8')
    if result['verification'] != 'VALID':
        raise AssertionError('Generator verification not valid')
    if result['sha256_input'] != digest(raw):
        raise AssertionError('Incorrect generator input digest')
    if audit(raw, source.decode('utf-8')) is not True:
        raise AssertionError('Generator/auditor disagreement')

    original_input = digest(raw)
    original_source = digest(source)
    # Persist the exact instance for third-party replay, not just its digest.
    Path('p314_tb_ci_input.json').write_bytes(raw)
    Path('p314_tb_ci_source.lean').write_bytes(source)
    if digest(Path('p314_tb_ci_input.json').read_bytes()) != original_input:
        raise BoundaryViolation('ARCHIVED_INPUT_HASH_MISMATCH')
    if digest(Path('p314_tb_ci_source.lean').read_bytes()) != original_source:
        raise BoundaryViolation('ARCHIVED_LEAN_HASH_MISMATCH')
    compiled = False
    with tempfile.TemporaryDirectory(prefix='lnz_p314_tb_ci_') as folder:
        private_dir = Path(folder)
        os.chmod(private_dir, 0o700)
        staged = private_dir / 'P314TBGenerated.lean'
        staged.write_bytes(source)
        invoked = []

        def simulated_compiler(path):
            invoked.append(path.name)
            return 0

        verified_handoff(raw, staged, original_input, original_source, simulated_compiler)
        assert len(invoked) == 1
        print('P314_TB_CI_BASELINE_PASS')

        # A changed coefficient must be blocked before invoking the runner.
        staged.write_bytes(source.replace(b'((2 : \xe2\x84\x9a) / (1 : \xe2\x84\x9a))',
                                          b'((4 : \xe2\x84\x9a) / (1 : \xe2\x84\x9a))', 1))
        assert staged.read_bytes() != source
        expect_rejection('coefficient_before_compilation',
                         lambda: verified_handoff(raw, staged, original_input, original_source, simulated_compiler))
        assert len(invoked) == 1

        # Restricted data audit accepts this extraneous source comment;
        # full-file hash must reject it before invocation.
        staged.write_bytes(source + b'\n-- injected after data audit\n')
        assert audit(raw, staged.read_text(encoding='utf-8')) is True
        expect_rejection('appended_content_before_compilation',
                         lambda: verified_handoff(raw, staged, original_input, original_source, simulated_compiler))
        assert len(invoked) == 1

        # Case identity affects original input hash even when Lean mathematics is same.
        staged.write_bytes(source)
        changed = raw.replace(b'P311_INDEPENDENT', b'ALTERED_CASE', 1)
        assert changed != raw
        expect_rejection('json_case_id_changed',
                         lambda: verified_handoff(changed, staged, original_input, original_source, simulated_compiler))
        assert len(invoked) == 1

        # Mutating persisted source while runner executes must invalidate success.
        def mutating_runner(path):
            path.write_bytes(source + b'\n-- modified while compiling\n')
            return 0
        expect_rejection('source_changed_during_compilation',
                         lambda: verified_handoff(raw, staged, original_input, original_source, mutating_runner))
        staged.write_bytes(source)

        # Save original bytes as historical input; not interpreted as a new CI artifact.
        if args.lean:
            # Compiler is invoked on the checked path. Security assumes this
            # private directory cannot be modified by an untrusted process.
            def run_lean(path):
                command = ['lake', 'env', 'lean', str(path)]
                environment = os.environ.copy()
                environment['LEAN_PATH'] = str(Path.cwd()) + os.pathsep + environment.get('LEAN_PATH', '')
                run = subprocess.run(command, env=environment, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, check=False)
                Path('p314_tb_ci_lean.log').write_text(run.stdout, encoding='utf-8')
                if run.returncode != 0:
                    raise BoundaryViolation('LEAN_COMPILATION_FAILED')
                if 'LNZ.p34_instance_optimal' not in run.stdout or 'depends on axioms:' not in run.stdout:
                    raise BoundaryViolation('LEAN_OUTPUT_MISSING')
                if any(term in run.stdout for term in ('sorryAx', 'Lean.ofReduceBool', 'unsafe')):
                    raise BoundaryViolation('LEAN_FORBIDDEN_MARKER')
                return run.returncode
            verified_handoff(raw, staged, original_input, original_source, run_lean)
            compiled = True
            print('P314_TB_CI_LEAN_COMPILE_PASS')

    if digest(Path('p314_tb_ci_input.json').read_bytes()) != original_input:
        raise BoundaryViolation('ARCHIVED_INPUT_CHANGED')
    if digest(Path('p314_tb_ci_source.lean').read_bytes()) != original_source:
        raise BoundaryViolation('ARCHIVED_SOURCE_CHANGED')

    report = {
        'case_id': doc['case_id'],
        'input_sha256': original_input,
        'lean_source_sha256': original_source,
        'byte_size_json': len(raw),
        'byte_size_lean': len(source),
        'python_boundary_test': 'PASS',
        'tamper_scenarios_rejected': 4,
        'lean_compilation': 'PASS' if compiled else 'NOT_RUN',
        'limitations': 'Assumes trusted isolated CI runtime; no general translator proof or hostile concurrent-writer defense'
    }
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('P314_TB_CI_PYTHON_PASS')
    if not compiled:
        print('P314_TB_CI_LEAN_NOT_RUN')


if __name__ == '__main__':
    main()
