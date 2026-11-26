"""Restricted proof builder for trusted, server-owned formal targets.
Not an arbitrary Lean parser or production sandbox.
"""
import hashlib
import re

TARGETS = {
    "reverse_append": "(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse",
    "false_control": ": False",
}
TACTICS = frozenset(("simp", "rfl", "assumption", "decide", "omega", "exact List.reverse_append", "intro", "constructor", "trivial"))
def build(target_id, tactics):
    if type(target_id) is not str or target_id not in TARGETS:
        raise ValueError("unknown target")
    if type(tactics) is not list or not 1 <= len(tactics) <= 16:
        raise ValueError("invalid tactic count")
    if any(type(t) is not str or t not in TACTICS for t in tactics):
        raise ValueError("unsupported tactic")
    target = TARGETS[target_id]
    source = "import Lean\nset_option autoImplicit false\ntheorem lnz_candidate " + target + " := by\n"
    source += "".join("  " + t + "\n" for t in tactics)
    source += "#print axioms lnz_candidate\n"
    return source, hashlib.sha256(target.encode()).hexdigest()

def audit(log):
    m = re.fullmatch(r"\s*'lnz_candidate' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", log)
    return bool(m and set(x.strip() for x in (m.group(1) or "").split(",") if x.strip()) <= {"propext", "Classical.choice", "Quot.sound"})
