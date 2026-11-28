"""Restricted proof builder for trusted, server-owned formal targets.
Not an arbitrary Lean parser or production sandbox.
"""
import hashlib
import re
from benchmark_targets import BENCHMARK_TARGETS, BENCHMARK_DEFINITIONS

TARGETS = {
    "reverse_append": "(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse",
    "linear_chain": "(a b c : Int) (h₁ : a ≤ b + 2) (h₂ : b ≤ c + 3) : a ≤ c + 5",
    "logic_chain": "(P Q R : Prop) (h₁ : P → Q) (h₂ : Q → R) : P → R",
    "nat_induction": "(n : Nat) : (List.replicate n true).length = n",
    "recursive_double": "(n : Nat) : lnzDouble n = n + n",
    "false_control": ": False",
}
TARGETS.update(BENCHMARK_TARGETS)
TACTICS = frozenset(("simp", "rfl", "assumption", "decide", "omega", "exact List.reverse_append", "intro", "constructor", "trivial", "apply h₂", "apply h₁"))
def mathematical_context(target_id):
    source = "import Lean\nset_option autoImplicit false\n"
    if target_id == "recursive_double":
        source += "def lnzDouble : Nat → Nat\n  | 0 => 0\n  | n+1 => lnzDouble n + 2\n"
    if target_id in BENCHMARK_DEFINITIONS and BENCHMARK_DEFINITIONS[target_id]:
        source += BENCHMARK_DEFINITIONS[target_id] + "\n"
    return source + "theorem lnz_candidate " + TARGETS[target_id] + " := by\n"

def context_sha256(target_id):
    return hashlib.sha256(mathematical_context(target_id).encode("utf8")).hexdigest()

def build(target_id, tactics):
    if type(target_id) is not str or target_id not in TARGETS:
        raise ValueError("unknown target")
    if type(tactics) is not list or not 1 <= len(tactics) <= 16:
        raise ValueError("invalid tactic count")
    generic = re.compile(r"(?:(?:induction|cases|apply|exact|rw) [A-Za-z_][A-Za-z0-9_]*|all_goals (?:simp|omega|rfl|assumption)|simp \[[A-Za-z_][A-Za-z0-9_]*\])")
    if any(type(t) is not str or not (t in TACTICS or generic.fullmatch(t)) for t in tactics):
        raise ValueError("unsupported tactic")
    if any(re.search(r'\b(?:sorry|sorryAx|admit)\b', t) for t in tactics):
        raise ValueError("forbidden placeholder")
    target = TARGETS[target_id]
    source = mathematical_context(target_id)
    source += "".join("  " + t + "\n" for t in tactics)
    source += "#print axioms lnz_candidate\n"
    return source, hashlib.sha256(target.encode()).hexdigest()

def audit(log):
    m = re.fullmatch(r"\s*'lnz_candidate' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", log)
    return bool(m and set(x.strip() for x in (m.group(1) or "").split(",") if x.strip()) <= {"propext", "Classical.choice", "Quot.sound"})


def forbidden_axioms(log):
    # Only classify a uniquely identified axiom report; ambiguous output fails closed.
    reports = re.findall(r"^'lnz_candidate' depends on axioms: \[([^\]\n]*)\]\s*$", log, re.MULTILINE)
    if len(reports) != 1:
        return False
    names = {x.strip() for x in reports[0].split(",") if x.strip()}
    return bool(names - {"propext", "Classical.choice", "Quot.sound"})
