"""Extract direct dependencies from elaborated Lean theorem values and types.
Trusted inspection suffix only; never accept caller-supplied inspection code.
"""
import re
from lemma_composition import sha

def inspection_suffix(names):
    if names != ["lnz_lemma_"+str(i) for i in range(len(names))] or not 1<=len(names)<=8:
        raise ValueError("names")
    all_names=names+["lnz_candidate"]
    literal="["+", ".join('"'+n+'"' for n in all_names)+"]"
    return """
open Lean Elab Command in
run_cmd do
  let env ← getEnv
  let names : List String := """+literal+"""
  for n in names do
    match env.find? (Name.mkSimple n) with
    | some (.thmInfo info) =>
      for d in names do
        let pred := fun e : Expr => e.isConstOf (Name.mkSimple d)
        if (info.value.find? pred).isSome || (info.type.find? pred).isSome then
          logInfo m!"LNZ_DEP_EDGE {n} {d}"
      logInfo m!"LNZ_DEP_NODE {n}"
    | _ => throwError "missing theorem declaration"
"""

def extract_dependencies(log,names):
    inspection_suffix(names)
    allowed=set(names+["lnz_candidate"])
    graph={n:[] for n in names+["lnz_candidate"]}
    seen=set()
    for line in log.splitlines():
        if "LNZ_DEP_" not in line: continue
        m=re.fullmatch(r".*info: LNZ_DEP_NODE (\w+)",line)
        if m:
            n=m[1]
            if n not in allowed or n in seen: raise ValueError("node report")
            seen.add(n);continue
        m=re.fullmatch(r".*info: LNZ_DEP_EDGE (\w+) (\w+)",line)
        if not m: raise ValueError("report format")
        n,d=m.groups()
        if n not in allowed or d not in allowed or d in graph[n]: raise ValueError("edge report")
        graph[n].append(d)
    if seen!=allowed: raise ValueError("incomplete report")
    order=names+["lnz_candidate"]
    for n,deps in graph.items():
        if any(order.index(d)>=order.index(n) for d in deps): raise ValueError("nonpreceding dependency")
    reachable=set()
    def visit(n):
        if n in reachable:return
        reachable.add(n)
        for d in graph[n]:visit(d)
    visit("lnz_candidate")
    return dict(graph=graph,used=[n for n in names if n in reachable],unused=[n for n in names if n not in reachable])

def compare_plan(manifest,observed):
    mapping={d["name"]:d["id"] for d in manifest["declarations"]}
    mapping["lnz_candidate"]="ROOT"
    actual={mapping[n]:sorted(mapping[d] for d in deps) for n,deps in observed["graph"].items()}
    proposed={n:sorted(deps) for n,deps in manifest["proposedGraph"].items()}
    return dict(actualGraph=actual,planMatches=actual==proposed,
                unused=[mapping[n] for n in observed["unused"]])
