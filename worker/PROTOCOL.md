# LNZ isolated Lean worker — protocol draft 1

Status: design contract, not deployed or certified.

POST /verify over HTTPS with server-owned bearer credential.
Request: protocol LNZ-WORKER-1, requestId, statement, statementHash, proof, proofHash, timeoutSeconds.
Recompute SHA-256 over UTF-8 statement and proof. Reject malformed or oversized requests. Limit timeout to 120 seconds.
Response: protocol, requestId, statementHash, proofHash, status ACCEPTED / REJECTED / UNAVAILABLE, diagnostic.

The API process must not execute untrusted Lean code itself. Each attempt runs in a disposable sandbox with no network, credentials, host sockets or writable shared dependencies. Enforce wall time, CPU, memory, process and output limits outside Lean. Pin the toolchain, mathlib revision and sandbox image digest before activation.

Treat both proposition and proof as untrusted syntax. Parse exactly one proposition and one proof, reject trailing commands, and construct the theorem through a trusted harness. Independently compare the elaborated theorem type against the frozen target; inspect kernel dependencies and reject axioms outside propext, Classical.choice, Quot.sound. Reject sorryAx and incomplete proofs. Never trust printed strings as proof of axiom audit. Keep trusted audit separate from candidate execution. Return UNAVAILABLE on infrastructure or audit failure.

Acceptance requires positive nontrivial theorem, false theorem rejection, target substitution rejection, forbidden axiom rejection, sandbox escape and resource-limit tests, authenticated end-to-end Floot request and replayable evidence. A worker response alone does not establish semantic equivalence to a natural-language problem. The current Floot client deliberately does not certify acceptance.

Repository main must remain unchanged until review. No deployment credentials in Git.
