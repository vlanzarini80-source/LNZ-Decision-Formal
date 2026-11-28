import {createHash} from 'node:crypto';
type Obligation={id:string;statement:string;dependsOn:string[]};
const sha=(s:string)=>createHash('sha256').update(s,'utf8').digest('hex');
export function validateDecomposition(problem:string, obligations:Obligation[], rootId:string){
 if(typeof problem!=='string'||!problem.trim()||problem.length>20000)throw Error('INVALID_PROBLEM');
 if(!Array.isArray(obligations)||!obligations.length||obligations.length>128)throw Error('INVALID_GRAPH_SIZE');
 const nodes=new Map<string,Obligation>();
 for(const n of obligations){
  if(!n||typeof n.id!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(n.id)||typeof n.statement!=='string'||!n.statement.trim()||n.statement.length>20000||!Array.isArray(n.dependsOn)||n.dependsOn.length>128||!n.dependsOn.every(d=>typeof d==='string')||new Set(n.dependsOn).size!==n.dependsOn.length)throw Error('INVALID_NODE');
  if(nodes.has(n.id))throw Error('DUPLICATE_NODE');
  nodes.set(n.id,{id:n.id,statement:n.statement,dependsOn:[...n.dependsOn]});
 }
 if(nodes.get(rootId)?.statement!==problem)throw Error('ROOT_MISMATCH');
 const visiting=new Set<string>(),done=new Set<string>(),order:string[]=[];
 function visit(id:string){
  if(visiting.has(id))throw Error('CYCLIC_DEPENDENCY');
  if(done.has(id))return;
  const n=nodes.get(id);if(!n)throw Error('MISSING_DEPENDENCY');
  visiting.add(id);for(const d of n.dependsOn)visit(d);
  visiting.delete(id);done.add(id);order.push(id);
 }
 visit(rootId);
 if(done.size!==nodes.size)throw Error('UNREACHABLE_NODE');
 const graph=order.map(id=>({...nodes.get(id)!,status:'UNVERIFIED' as const}));
 return {protocol:'LNZ-CORE-P1.1',problem,problem_sha256:sha(problem),graph_sha256:sha(JSON.stringify(graph)),rootId,graph,status:'STRUCTURAL_VALIDATION_ONLY',semantic_equivalence_verified:false,lean_executed:false,certified:false};
}
