"""Structural dependency plan, NOT a verified Lean dependency graph.
Edges point from a declaration to its prerequisites.
Current registry supports independently proved lemmas only.
"""
import json
from lemma_composition import build_composition, sha

def order_dependencies(graph, root):
    if type(graph) is not dict or not 2 <= len(graph) <= 9 or root not in graph:
        raise ValueError("graph size or root")
    for node,deps in graph.items():
        if not isinstance(node,str) or not 1<=len(node)<=128 or type(deps) is not list:
            raise ValueError("node schema")
        if any(not isinstance(d,str) or d not in graph for d in deps):
            raise ValueError("unknown dependency")
        if len(set(deps))!=len(deps):
            raise ValueError("duplicate edge")
    active=set()
    done=set()
    order=[]
    def visit(node):
        if node in active: raise ValueError("cycle")
        if node in done: return
        active.add(node)
        for dep in graph[node]: visit(dep)
        active.remove(node)
        done.add(node)
        order.append(node)
    visit(root)
    if done!=set(graph): raise ValueError("unreachable node")
    return order

def prepare_registered_composition(registry, statement, proof, graph):
    root="ROOT"
    order=order_dependencies(graph,root)
    # Do not pretend dependent lemmas have individual receipts.
    if any(graph[n] for n in order[:-1]):
        raise ValueError("dependent lemma receipts not supported")
    records=[registry.load(n) for n in order[:-1]]
    prefix,source,names=build_composition(statement,proof,records)
    manifest=dict(rootStatementHash=sha(statement),rootProofHash=sha(proof),
                  contextHash=sha(prefix),sourceHash=sha(source),
                  proposedGraph=graph,order=order,
                  declarations=[dict(id=n,name=name,**r) for n,name,r in zip(order[:-1],names,records)],
                  status="STRUCTURAL_PLAN_ONLY",certified=False)
    return source,manifest
