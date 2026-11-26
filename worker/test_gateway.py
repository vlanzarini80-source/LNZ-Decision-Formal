import hashlib
import json
import unittest
import uuid
from gateway import dispatch

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.token = "test-only-" * 4
        self.q = dict(protocol="LNZ-WORKER-1", requestId=str(uuid.uuid4()),
                      statement="True", proof="by trivial", timeoutSeconds=120)
        for k in ("statement", "proof"):
            self.q[k+"Hash"] = hashlib.sha256(self.q[k].encode()).hexdigest()

    def call(self):
        return dispatch(json.dumps(self.q).encode(), "Bearer "+self.token, self.token)

    def test_unavailable_not_accepted(self):
        status, r = self.call()
        self.assertEqual(status, 200)
        self.assertEqual(r["status"], "UNAVAILABLE")
        self.assertEqual(r["requestId"], self.q["requestId"])

    def test_auth(self):
        self.assertEqual(dispatch(b"", "Bearer wrong", self.token)[0], 401)

    def test_no_config(self):
        self.assertEqual(dispatch(b"", "", None)[0], 503)

    def test_changed_target(self):
        self.q["statement"] = "False"
        self.assertEqual(self.call()[0], 400)

    def test_changed_proof(self):
        self.q["proof"] = "by sorry"
        self.assertEqual(self.call()[0], 400)

    def test_timeout(self):
        self.q["timeoutSeconds"] = 121
        self.assertEqual(self.call()[0], 400)

    def test_duplicate(self):
        self.assertEqual(dispatch(b'{"protocol":1,"protocol":2}', "Bearer "+self.token, self.token)[0], 400)

    def test_unknown_field(self):
        self.q["certified"] = True
        self.assertEqual(self.call()[0], 400)

if __name__ == "__main__":
    unittest.main()
