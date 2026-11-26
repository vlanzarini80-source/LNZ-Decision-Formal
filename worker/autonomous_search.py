"""Provider-neutral controller. Verification callback must be trusted.
No certification is issued by this orchestration layer.
"""
import hashlib
import json
from dynamic_proof import build, TARGETS, TACTICS

def search(target_id, generate, verify, budget=8):
    if target_id not in TARGETS or type(budget) is not int or not 1 <= budget <= 8:
        raise ValueError("invalid search")
    target = TARGETS[target_id]
    target_hash = hashlib.sha256(target.encode()).hexdigest()
    trace, seen, diagnostics = [], set(), []
    def finish(status):
        return dict(status=status, target_hash=target_hash, trace=trace, certified=False)
    for attempt in range(budget):
        try:
            raw = generate(dict(target=target, allowed_tactics=sorted(TACTICS),
                                diagnostics=list(diagnostics), remaining=budget-attempt))
            if not isinstance(raw, str) or len(raw) > 4096:
                raise ValueError("invalid provider output")
            tactics = json.loads(raw)
            source, digest = build(target_id, tactics)
            if digest != target_hash:
                return finish("TARGET_MISMATCH")
            proof_hash = hashlib.sha256(source.encode()).hexdigest()
            if proof_hash in seen:
                diagnostics.append("Repeated candidate; choose a different tactic sequence.")
                trace.append(dict(status="REPEATED", proof_hash=proof_hash))
                continue
            seen.add(proof_hash)
            receipt = verify(source)
            if not isinstance(receipt, dict) or receipt.get("source_hash") != proof_hash or receipt.get("status") not in ("ACCEPTED", "REJECTED", "UNAVAILABLE"):
                return finish("INVALID_RECEIPT")
            diagnostic = receipt.get("diagnostic")
            if not isinstance(diagnostic, str) or len(diagnostic) > 8000:
                return finish("INVALID_RECEIPT")
            trace.append(dict(proof_hash=proof_hash, status=receipt["status"], diagnostic=diagnostic))
            if receipt["status"] == "ACCEPTED":
                return finish("RUNNER_ACCEPTANCE_UNATTESTED")
            if receipt["status"] == "UNAVAILABLE":
                return finish("VERIFIER_UNAVAILABLE")
            diagnostics.append(diagnostic)
        except ValueError:
            diagnostics.append("Invalid candidate format or unsupported tactic.")
            trace.append(dict(status="INVALID_CANDIDATE"))
        except Exception:
            return finish("TOOL_ERROR")
    return finish("BUDGET_EXHAUSTED")
