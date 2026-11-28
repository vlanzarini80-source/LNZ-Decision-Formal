"""Experimental dynamic theorem source builder. Not a general Lean parser."""
import re
import unicodedata

# Single-line expressions only; no command syntax, comments, strings or macros.
TOKEN = re.compile(r"[\w \t():,.+\-*/^=<>≤≥≠∀∃→↔∧∨¬∣∑ℕℤℝ×]+", re.UNICODE)
BLOCK = re.compile(r"\b(?:by|sorry|sorryAx|admit|axiom|theorem|lemma|def|unsafe|run_tac|set_option|import|namespace|end|where|let|in|match|do|macro|syntax|elab|open|section|opaque|example|instance|attribute)\b")
TACTIC = re.compile(r"(?:simp|rfl|omega|decide|assumption|intro|constructor|trivial|(?:intro|induction|cases|apply|exact|rw) [A-Za-z_][A-Za-z0-9_]*|simp \[[A-Za-z_][A-Za-z0-9_]*\]|all_goals (?:simp|omega|rfl|assumption))")

def build_dynamic(statement, proof):
    if not isinstance(statement, str) or not 1 <= len(statement) <= 12000:
        raise ValueError("statement size")
    if unicodedata.normalize("NFC", statement) != statement:
        raise ValueError("normalization")
    if not TOKEN.fullmatch(statement) or BLOCK.search(statement):
        raise ValueError("statement grammar")
    if any(x in statement for x in (":=", "--", "/-", "-/", "\t")):
        raise ValueError("statement delimiter")
    # Require balanced binders and a top-level result colon.
    depth = 0
    result = False
    for c in statement:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("binder balance")
        elif c == ":" and depth == 0:
            result = True
    if depth or not result:
        raise ValueError("statement structure")
    if not isinstance(proof, str) or len(proof) > 24000:
        raise ValueError("proof size")
    lines = proof.split("\n")
    if lines[0] != "by" or not 1 <= len(lines)-1 <= 32:
        raise ValueError("proof structure")
    for line in lines[1:]:
        if not line.startswith("  ") or not TACTIC.fullmatch(line[2:]) or BLOCK.search(line[2:]):
            raise ValueError("tactic grammar")
    prefix = "import Lean\nset_option autoImplicit false\ntheorem lnz_candidate " + statement + " := by\n"
    return prefix, prefix + proof[3:] + "\n#print axioms lnz_candidate\n"
