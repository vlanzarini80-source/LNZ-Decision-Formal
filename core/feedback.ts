import {createHash} from 'node:crypto';
const sha=(s:string)=>createHash('sha256').update(s,'utf8').digest('hex');
type Candidate={statement:string;proof:string};
type Request={statement:string;statementHash:string;proof:string;proofHash:string};
type Receipt={statementHash:string;proofHash:string;status:'ACCEPTED'|'REJECTED'|'UNAVAILABLE';diagnostic:string};
type Generate=(statement:string,diagnostics:readonly string[])=>Promise<Candidate>;
type Verify=(request:Readonly<Request>)=>Promise<Receipt>;
// This is orchestration only. The trusted runner must independently bind and audit Lean evidence.
export async function feedbackLoop(statement:string,budget:number,generate:Generate,verify:Verify){
 if(typeof statement!=='string'||!statement.trim()||statement.length>12000||!Number.isSafeInteger(budget)||budget<1||budget>8)throw Error('INVALID_FEEDBACK_INPUT');
 const statementHash=sha(statement),diagnostics:string[]=[],seen=new Set<string>();
 const trace:{proofHash:string;status:string;diagnostic:string}[]=[];
 const finish=(status:string)=>({protocol:'LNZ-CORE-P1.4',statementHash,status,trace,certified:false,lean_execution_independently_verified:false});
 for(let i=0;i<budget;i++){
 try{
 const c=await generate(statement,Object.freeze([...diagnostics]));
 if(!c||c.statement!==statement||typeof c.proof!=='string'||!c.proof.trim()||c.proof.length>24000)return finish('CANDIDATE_REJECTED');
 const proofHash=sha(c.proof);
 if(seen.has(proofHash))return finish('REPEATED_CANDIDATE');
 seen.add(proofHash);
 const r=await verify(Object.freeze({statement,statementHash,proof:c.proof,proofHash}));
 if(!r||r.statementHash!==statementHash||r.proofHash!==proofHash||!['ACCEPTED','REJECTED','UNAVAILABLE'].includes(r.status)||typeof r.diagnostic!=='string'||r.diagnostic.length>8000)return finish('RECEIPT_REJECTED');
 trace.push({proofHash,status:r.status,diagnostic:r.diagnostic});
 if(r.status==='UNAVAILABLE')return finish('VERIFIER_UNAVAILABLE');
 if(r.status==='ACCEPTED')return finish('RUNNER_ACCEPTANCE_UNATTESTED');
 diagnostics.push(r.diagnostic);
 }catch{return finish('TOOL_ERROR')}
 }
 return finish('BUDGET_EXHAUSTED');
}
