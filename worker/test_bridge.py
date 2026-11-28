import hashlib,json,unittest,uuid
from bridge import bridge
from dynamic_proof import TARGETS

class BridgeTests(unittest.TestCase):
    def call(self, execute, statement=TARGETS["reverse_append"], proof="by\n  simp", auth=True):
        token="test-only-"*4
        q=dict(protocol="LNZ-WORKER-1",requestId=str(uuid.uuid4()),statement=statement,proof=proof,timeoutSeconds=120)
        for k in ("statement","proof"):
            q[k+"Hash"]=hashlib.sha256(q[k].encode()).hexdigest()
        return bridge(json.dumps(q).encode(),"Bearer "+(token if auth else "wrong"),token,execute)
    def test_acceptance(self):
        def execute(source, timeout):
            self.assertIn(TARGETS["reverse_append"],source)
            self.assertEqual(timeout,120)
            return 0,"'lnz_candidate' does not depend on any axioms"
        self.assertEqual(self.call(execute)[1]["status"],"ACCEPTED")
    def test_diagnostic(self):
        self.assertEqual(self.call(lambda s,t:(1,"error: unsolved goals"))[1]["diagnostic"],"error: unsolved goals")
    def test_axiom(self):
        self.assertEqual(self.call(lambda s,t:(0,"'lnz_candidate' depends on axioms: [sorryAx]"))[1]["status"],"REJECTED")
    def test_auth(self):
        self.assertEqual(self.call(lambda s,t:self.fail("execution"),auth=False)[0],401)
    def test_target(self):
        self.assertEqual(self.call(lambda s,t:self.fail("execution"),statement="True")[1]["status"],"UNAVAILABLE")
    def test_injection(self):
        self.assertEqual(self.call(lambda s,t:self.fail("execution"),proof="by\n  sorry")[1]["status"],"REJECTED")
    def test_failure(self):
        self.assertEqual(self.call(lambda s,t:(124,"timeout"))[1]["status"],"UNAVAILABLE")

    def test_exact_sorry(self):
        for tactic in ("exact sorry", "exact sorryAx", "exact admit"):
            self.assertEqual(self.call(lambda s,t:self.fail("execution"),proof="by\n  "+tactic)[1]["status"],"REJECTED")
    def test_axiom_warning(self):
        self.assertEqual(self.call(lambda s,t:(0,"warning: declaration uses 'sorry'\n'lnz_candidate' depends on axioms: [sorryAx]\n"))[1]["status"],"REJECTED")
    def test_unknown_audit(self):
        self.assertEqual(self.call(lambda s,t:(0,"unparseable audit"))[1]["status"],"UNAVAILABLE")
