# Evidence-gated mathematical decisions

Normative design specification; not an implemented or formally verified policy.

For a fixed proposition P in a pinned mathematical context, PROVEN requires a checked proof of P and validated provenance, context, target, proof and axiom policy. DISPROVEN requires equivalent evidence for Not P or a formally checked counterexample implying Not P. A rejected candidate never implies Not P. Exhaustion, timeout, unavailable verifier, malformed receipt, or unverified plan cannot establish truth or falsity. Conflicting accepted evidence must halt for audit, never select a winner. Runner acceptance without sufficient provenance remains RUNNER_ACCEPTANCE_UNATTESTED, certified=false.

Decision statuses: PROVEN, DISPROVEN, INSUFFICIENT_EVIDENCE, BUDGET_EXHAUSTED, VERIFIER_UNAVAILABLE. Operational failures remain separately recorded. No AI confidence score substitutes for proof. Record all attempts and stopping reasons. Formal verification of decision-policy invariants is a separate required milestone; it does not prove strategy optimality or universal decidability.

Required tests: valid proof, valid refutation, failed candidate for true target, failed candidate for false target, tampered receipt, context mismatch, forbidden axiom, exhausted budget, timeout, conflicting evidence. No promotion to production before tests and independent audit.
