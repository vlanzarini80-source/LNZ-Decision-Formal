import type {Alternative} from './search.ts';
export interface Budget {maxProviderCalls:number;maxVerifierCalls:number;maxLemmas:number;deadlineMs:number}
export interface Provider {
 readonly id:string;
 expand(goal:string,signal:AbortSignal):Promise<Alternative[]>;
 propose(statement:string,diagnostics:readonly string[],signal:AbortSignal,previousProofs?:readonly string[]):Promise<{statement:string;proof:string}>;
}
export interface VerificationRequest {statement:string;statementHash:string;proof:string;proofHash:string}
export interface Verifier {
 readonly id:string;
 verify(request:Readonly<VerificationRequest>,signal:AbortSignal):Promise<{statementHash:string;proofHash:string;status:'ACCEPTED'|'REJECTED'|'UNAVAILABLE';diagnostic:string}>;
}
export interface EvidenceStore {
 // Must durably commit before resolving. Implementations must enforce unique run/sequence.
 append(event:Readonly<{runId:string;sequence:number;at:number;kind:string;data:unknown}>):Promise<void>;
}
export interface RuntimeAdapters {provider:Provider;verifier:Verifier;store:EvidenceStore}
