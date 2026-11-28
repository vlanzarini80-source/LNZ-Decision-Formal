// Bounded AND-OR planner. Structural plans are not mathematical proofs.
export type Alternative={id:string;goals:string[]};
export type Expand=(goal:string)=>Promise<Alternative[]>;
export async function searchProofPlan(root:string,expand:Expand,budget:number,maxDepth=12){
 if(typeof root!=='string'||!root.trim()||root.length>20000||!Number.isSafeInteger(budget)||budget<0||budget>256||!Number.isSafeInteger(maxDepth)||maxDepth<0||maxDepth>32)throw Error('INVALID_SEARCH_INPUT');
 let spent=0;const trace:{goal:string;alternative:string;outcome:string}[]=[];
 type Plan={goal:string;alternative:string;children:Plan[]};
 async function visit(goal:string,ancestors:Set<string>,depth:number):Promise<Plan|null>{
  if(depth>maxDepth||ancestors.has(goal)||spent>=budget)return null;
  spent++;
  const options=await expand(goal);
  if(!Array.isArray(options)||options.length>32)throw Error('INVALID_EXPANSION');
  const ids=new Set<string>();
  for(const a of options){
   if(!a||typeof a.id!=='string'||!a.id||ids.has(a.id)||!Array.isArray(a.goals)||a.goals.length>16||!a.goals.every(g=>typeof g==='string'&&g.trim()&&g.length<=20000))throw Error('INVALID_ALTERNATIVE');
   ids.add(a.id);
  }
  const next=new Set(ancestors);next.add(goal);
  for(const a of options){
   const children:Plan[]=[];let ok=true;
   for(const g of a.goals){const child=await visit(g,next,depth+1);if(!child){ok=false;break}children.push(child)}
   trace.push({goal,alternative:a.id,outcome:ok?'CANDIDATE_PLAN':'BACKTRACK'});
   if(ok)return {goal,alternative:a.id,children};
  }
  return null;
 }
 const plan=await visit(root,new Set(),0);
 return {protocol:'LNZ-CORE-P1.2',root,plan,spent,budget,remaining:budget-spent,trace,status:plan?'UNVERIFIED_PLAN':'UNRESOLVED',lean_executed:false,certified:false};
}
