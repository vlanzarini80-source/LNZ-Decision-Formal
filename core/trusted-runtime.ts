import {runPortable} from './runtime.ts';
import {requireTrustedVerifier} from './trusted-adapter.ts';
import type {RuntimeAdapters} from './runtime-contracts.ts';
import type {DurableBudgetStore} from './budget.ts';
export async function runTrusted(runId:string,statement:string,adapters:RuntimeAdapters,store:DurableBudgetStore){
 const verify=requireTrustedVerifier(adapters.verifier);
 const snapshot=Object.freeze({provider:adapters.provider,store:adapters.store,verifier:Object.freeze({id:'lnz-signed-worker-v1',verify})});
 return runPortable(runId,statement,snapshot,store);
}
