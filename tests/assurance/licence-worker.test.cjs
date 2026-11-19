const {test}=require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {issue,pin,saveOutput}=require('../../scripts/assurance/licence-worker.cjs');
const signer=crypto.generateKeyPairSync('rsa',{modulusLength:4096});
const approver=crypto.generateKeyPairSync('rsa',{modulusLength:4096});
const passphrase=Buffer.from('synthetic-test-passphrase');
const signingPem=signer.privateKey.export({type:'pkcs8',format:'pem',cipher:'aes-256-cbc',passphrase});
const approvalPublicPem=approver.publicKey.export({type:'spki',format:'pem'});
function setup(t){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'tec-worker-'));fs.chmodSync(dir,0o700);t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const now=Date.parse('2026-11-18T12:00:00Z');
 const job={version:1,jobId:crypto.randomUUID(),approvalId:crypto.randomUUID(),installationId:crypto.randomUUID(),customerName:'Synthetic Clinic',licencePublicKeySha256:pin(signer.privateKey),modules:['patients','appointments'],approvedAt:'2026-11-18T11:59:00Z',approvalExpiresAt:'2026-11-18T13:00:00Z',expiresAt:'2026-12-31T23:59:59Z'};
 const options={approvalPublicPem,approvalPin:pin(approver.privateKey),signingPem,signingPin:pin(signer.privateKey),passphrase,dbPath:path.join(dir,'ledger.sqlite'),now};
 function signed(j=job){return Buffer.from(JSON.stringify({job:j,signature:crypto.sign('RSA-SHA256',Buffer.from(JSON.stringify(j)),approver.privateKey).toString('base64')}));}
 return {dir,job,options,signed};
}
test('persists once, retries return identical bytes including after approval expiry',t=>{const s=setup(t);const a=issue({...s.options,approvalBytes:s.signed()});const b=issue({...s.options,approvalBytes:s.signed(),now:s.options.now+2*3600000});assert.equal(a.licence,b.licence);assert.equal(b.reused,true);});
test('changed approved claims cannot reuse job ID',t=>{const s=setup(t);issue({...s.options,approvalBytes:s.signed()});s.job.customerName='Changed';assert.throws(()=>issue({...s.options,approvalBytes:s.signed()}),/replay/);});
test('unsigned tampering rejected',t=>{const s=setup(t);const e=JSON.parse(s.signed());e.job.modules=['*'];assert.throws(()=>issue({...s.options,approvalBytes:Buffer.from(JSON.stringify(e))}),/signature/);});
test('expired first issuance denied',t=>{const s=setup(t);assert.throws(()=>issue({...s.options,approvalBytes:s.signed(),now:s.options.now+2*3600000}),/Approval expired/);});
test('unknown modules denied even with valid approval signature',t=>{const s=setup(t);s.job.modules=['unknown'];assert.throws(()=>issue({...s.options,approvalBytes:s.signed()}),/modules/);});
test('wrong licence key pin denied',t=>{const s=setup(t);assert.throws(()=>issue({...s.options,approvalBytes:s.signed(),signingPin:'0'.repeat(64)}),/fingerprint/);});
test('wrong approval key pin denied',t=>{const s=setup(t);assert.throws(()=>issue({...s.options,approvalBytes:s.signed(),approvalPin:'0'.repeat(64)}),/fingerprint/);});
test('same approval cannot issue two jobs',t=>{const s=setup(t);issue({...s.options,approvalBytes:s.signed()});s.job.jobId=crypto.randomUUID();assert.throws(()=>issue({...s.options,approvalBytes:s.signed()}),/UNIQUE/);});
test('local delivery retries cannot overwrite another file',t=>{const s=setup(t);const out=path.join(s.dir,'out.teclicense');saveOutput(out,'fixture');saveOutput(out,'fixture');assert.throws(()=>saveOutput(out,'other'),/different/);});
test('invalid installation UUID denied',t=>{const s=setup(t);s.job.installationId='../file';assert.throws(()=>issue({...s.options,approvalBytes:s.signed()}),/identity/);});

test('approval cannot be transferred to a different licence key',t=>{const s=setup(t);s.job.licencePublicKeySha256='0'.repeat(64);assert.throws(()=>issue({...s.options,approvalBytes:s.signed()}),/fingerprint/);});
