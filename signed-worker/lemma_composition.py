"""Bounded composition source builder. Every dependency is re-proved.
Caller must separately authorize the accepted lemma records; this builder
does not establish receipt provenance.
"""
import hashlib
from dynamic_lemma_source import build_dynamic

HEADER = "import Lean\nset_option autoImplicit false\n"
def sha(s):
    return hashlib.sha256(s.encode("utf8")).hexdigest()

def build_composition(statement, proof, lemmas):
    if type(lemmas) is not list or not 1 <= len(lemmas) <= 8:
        raise ValueError("lemma count")
    root_prefix, root_source = build_dynamic(statement, proof)
    declarations = []
    names = []
    seen = set()
    for i, item in enumerate(lemmas):
        if type(item) is not dict or set(item) != {"statement", "proof", "statementHash", "proofHash"}:
            raise ValueError("lemma schema")
        s, p = item["statement"], item["proof"]
        _, source = build_dynamic(s, p)
        if sha(s) != item["statementHash"] or sha(p) != item["proofHash"]:
            raise ValueError("lemma binding")
        if s == statement or s in seen:
            raise ValueError("duplicate or root lemma")
        seen.add(s)
        name = "lnz_lemma_" + str(i)
        names.append(name)
        declaration = source[len(HEADER):].removesuffix("\n#print axioms lnz_candidate\n")
        declarations.append(declaration.replace("theorem lnz_candidate ", "theorem "+name+" ", 1))
    prefix = HEADER + "\n\n".join(declarations) + "\n\n" + root_prefix[len(HEADER):]
    source = prefix + proof[3:] + "\n#print axioms lnz_candidate\n"
    if len(source.encode("utf8")) > 160000:
        raise ValueError("source limit")
    return prefix, source, names
