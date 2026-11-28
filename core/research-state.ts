export type ResearchState={phase:'READY'|'WAITING'|'STOPPED';budget:number;attempts:number;polls:number;deadline:number;proofs:string[];diagnostics:string[];reason:string;certified:false};
export function initialResearch(budget:number,now:number):ResearchState{
 if(!Number.isSafeInteger(budget)||budget<1||budget>4||!Number.isSafeInteger(now)||now<0)throw Error('INVALID_BUDGET');
 return {phase:'READY',budget,attempts:0,polls:0,deadline:now+3600000,proofs:[],diagnostics:[],reason:'',certified:false};
}
type Event={kind:'candidate';proof:string}|{kind:'pending'}|{kind:'receipt';status:'ACCEPTED'|'REJECTED'|'UNAVAILABLE';diagnostic:string}|{kind:'timeout'};
export function advanceResearch(s:ResearchState,e:Event,now:number):ResearchState{
 if(s.phase==='STOPPED')return s;
 const stop=(reason:string):ResearchState=>({...s,phase:'STOPPED',reason,certified:false});
 if(now>=s.deadline||e.kind==='timeout')return stop('TIMEOUT');
 if(e.kind==='candidate'&&s.phase==='READY'){
 if(s.attempts>=s.budget)return stop('BUDGET_EXHAUSTED');
 if(!e.proof.trim()||e.proof.length>24000)return stop('INVALID_PROOF');
 if(s.proofs.includes(e.proof))return stop('REPEATED_PROOF');
 return {...s,phase:'WAITING',attempts:s.attempts+1,polls:0,proofs:[...s.proofs,e.proof]};
 }
 if(e.kind==='pending'&&s.phase==='WAITING')return s.polls>=19?stop('POLL_LIMIT'):{...s,polls:s.polls+1};
 if(e.kind==='receipt'&&s.phase==='WAITING'){
 if(e.status==='ACCEPTED')return stop('RUNNER_ACCEPTANCE_UNATTESTED');
 if(e.status!=='REJECTED'||e.diagnostic.length>8000)return stop('VERIFIER_UNAVAILABLE');
 const next={...s,diagnostics:[...s.diagnostics,e.diagnostic]};
 return {...next,phase:s.attempts>=s.budget?'STOPPED':'READY',reason:s.attempts>=s.budget?'BUDGET_EXHAUSTED':''};
 }
 throw Error('INVALID_TRANSITION');
}

