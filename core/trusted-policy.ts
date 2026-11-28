export type EvidenceFlags = {signature:boolean;context:boolean;worker:boolean;fresh:boolean;compiled:boolean;axioms:boolean;attested:boolean;sufficient:boolean};
export function decideEvidence(e:EvidenceFlags):'REJECT'|'ABSTAIN'|'CERTIFY'{
 if(![e.signature,e.context,e.worker,e.fresh,e.compiled,e.axioms].every(x=>x===true))return 'REJECT';
 return e.attested===true&&e.sufficient===true?'CERTIFY':'ABSTAIN';
}
