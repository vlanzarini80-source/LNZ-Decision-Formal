"""Real Lean composition controls, not autonomous AI benchmark."""
import json
from pathlib import Path
from lemma_composition import build_composition, sha
from dynamic_lemma_source import build_dynamic
from real_bridge import executor
from dynamic_proof import audit

root = "(P Q : Prop) (h : P) : Q → P"
lemma = "(P Q : Prop) : P → Q → P"
proof = "by\n  apply lnz_lemma_0\n  assumption"
def item(s,p):
    return dict(statement=s,proof=p,statementHash=sha(s),proofHash=sha(p))
good = item(lemma,"by\n  intro h\n  intro k\n  assumption")
events=[]
def save():
    Path("composition-audit-evidence.json").write_text(json.dumps(events,ensure_ascii=False,indent=2))
def run(label,source,ok,check_axioms=False):
    rc,log=executor(source,30)
    events.append(dict(label=label,source=source,sourceHash=sha(source),exitCode=rc,log=log))
    save()
    if ok:
        assert rc==0,(label,log)
        if check_axioms: assert audit(log),(label,log)
    else:
        assert rc==1 and "error:" in log,(label,rc,log)
def reject(label,fn):
    try: fn()
    except ValueError as e:
        events.append(dict(label=label,rejected=True,error=str(e)));save()
    else: raise AssertionError(label)
try:
    _,individual=build_dynamic(lemma,good["proof"])
    run("individual lemma",individual,True,True)
    prefix,source,names=build_composition(root,proof,[good])
    assert names==["lnz_lemma_0"]
    original_prefix,original_source=build_dynamic(root,proof)
    assert source.endswith(original_source.split("theorem lnz_candidate ",1)[1])
    run("valid composition",source,True,True)
    # Trusted inspection command: inspect elaborated theorem value, not source text.
    inspection = r"""
open Lean Elab Command in
run_cmd do
  let env ← getEnv
  match env.find? (Name.mkSimple "lnz_candidate") with
  | some (.thmInfo info) =>
    unless (info.value.find? (fun e => e.isConstOf (Name.mkSimple "lnz_lemma_0"))).isSome do
      throwError "missing elaborated lemma dependency"
    logInfo "LNZ_ELABORATED_DEPENDENCY_PRESENT"
  | _ => throwError "missing root theorem"
"""
    run("elaborated dependency",source+inspection,True)
    assert "LNZ_ELABORATED_DEPENDENCY_PRESENT" in events[-1]["log"]
    # Check elaborated type against a separately declared expected type.
    type_check = r"""
def lnz_expected_type : Prop := ∀ (P Q : Prop), P → Q → P
example : lnz_expected_type := @lnz_candidate
"""
    run("root type compatibility",source+type_check,True)
    bad=item(lemma,"by\n  assumption")
    run("invalid intermediate proof",build_composition(root,proof,[bad])[1],False)
    reject("altered lemma",lambda:build_composition(root,proof,[dict(good,proof="by\n  trivial")]))
    run("missing dependency",original_source,False)
    reject("root as lemma",lambda:build_composition(root,proof,[item(root,proof)]))
    reject("duplicate lemma",lambda:build_composition(root,proof,[good,good]))
    print("REAL_LEAN_COMPOSITION_AUDIT_PASS")
finally: save()
