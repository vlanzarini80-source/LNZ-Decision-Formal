import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createHash} from 'node:crypto';
import {leanAdapter} from './lean-adapter.ts';
const sha=(s:string)=>createHash('sha256').update(s).digest('hex');
const statement='test proposition',proof='by rfl';
const q={statement,proof,statementHash:sha(statement),proofHash:sha(proof)};
let mode='valid',previous:any;
const server=createServer(async(req,res)=>{
 let body='';for await(const c of req)body+=c;
 const x=JSON.parse(body);
 let r:any={protocol:x.protocol,requestId:x.requestId,statementHash:x.statementHash,proofHash:x.proofHash,status:'ACCEPTED',diagnostic:'synthetic'};
 switch(mode){
 case 'statement':r.statementHash=sha('different');break;
 case 'proof':r.proofHash=sha('different');break;
 case 'protocol':r.protocol='wrong';break;
 case 'replay':r=previous;break;
 case 'status':r.status='PROVEN';break;
 case 'diagnostic':r.diagnostic=123;break;
 case 'certified':r.certified=true;break;
 case 'null':r=null;break;
 case 'valid':previous=r;break;
 }
 res.end(JSON.stringify(r));
});
await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
try{
 const address=server.address();if(!address||typeof address==='string')throw Error('ADDRESS');
 const v=leanAdapter('http://127.0.0.1:'+address.port+'/verify','x'.repeat(32));
 const call=()=>v.verify(q,AbortSignal.timeout(5000));
 assert.equal((await call()).status,'ACCEPTED');
 for(const m of ['statement','proof','protocol','replay','status','diagnostic','certified','null']){
 mode=m;await assert.rejects(call(),/INVALID_RECEIPT/);console.log('REJECTED',m);
 }
 await assert.rejects(v.verify({...q,statement:'substitution'},AbortSignal.timeout(5000)),/REQUEST_HASH_MISMATCH/);
 console.log('RECEIPT_ADVERSARIAL_PASS 9 negative controls; matching synthetic receipt is not authenticated proof');
}finally{await new Promise<void>((resolve,reject)=>server.close(e=>e?reject(e):resolve()))}
