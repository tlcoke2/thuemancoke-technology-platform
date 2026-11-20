#!/usr/bin/env node
'use strict';
// Reads the exact private objects using the operator's existing AWS CLI profile.
// Never uploads, overwrites, signs, or activates a release; needs only public PEM.
const fs=require('node:fs'), os=require('node:os'), path=require('node:path');
const c=require('node:crypto'), {spawnSync}=require('node:child_process');
const expected={"archiveFilename": "TEC-EPR-Clinic-Edition-1.0.1-Regional-a55a2b114a35.tar.gz", "archiveSha256": "0636d7a399f85e0cbd9a77175d11bf735df1f3b82f89825954c7575da8f26951", "archiveBytes": 266757194, "signatureSha256": "ebbe87da6dbde8898b1df16e8702615300a812cd5c4a013d9a72b9a99151872c", "publisherSpkiSha256": "b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a"};
function run(exe,args){const r=spawnSync(exe,args,{encoding:'utf8',windowsHide:true});if(r.status!==0)throw new Error(exe+' failed; check local authentication/tool availability');return r.stdout;}
async function hash(file){const h=c.createHash('sha256');for await(const b of fs.createReadStream(file))h.update(b);return h.digest('hex');}
async function main(){
 const [pem,out]=process.argv.slice(2);if(!pem||!out)throw new Error('Usage: node verify-regional-r2.cjs PUBLIC.pem NEW-READBACK.json');
 if(fs.existsSync(out))throw new Error('Evidence already exists; choose a new output filename');
 const key=c.createPublicKey(fs.readFileSync(pem));
 if(key.asymmetricKeyType!=='rsa'||key.asymmetricKeyDetails.modulusLength!==4096||c.createHash('sha256').update(key.export({type:'spki',format:'der'})).digest('hex')!==expected.publisherSpkiSha256)throw new Error('Publisher public key mismatch');
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'tec-regional-readback-'));
 const prefix='tec-epr/clinic-edition/1.0.1/', bucket='tec-epr-private-releases';
 const endpoint='https://d0ad5986fca56c661b92988f2ea1c1f7.r2.cloudflarestorage.com';
 const common=['--bucket',bucket,'--endpoint-url',endpoint,'--output','json'];
 try {
  const archive=path.join(tmp,'archive.tar.gz'), sig=path.join(tmp,'publisher.sig');
  const response=JSON.parse(run('aws',['s3api','get-object',...common,'--key',prefix+expected.archiveFilename,archive]));
  run('aws',['s3api','get-object',...common,'--key',prefix+expected.archiveFilename+'.publisher.sig',sig]);
  if(fs.statSync(archive).size!==expected.archiveBytes||await hash(archive)!==expected.archiveSha256||fs.statSync(sig).size!==512||await hash(sig)!==expected.signatureSha256)throw new Error('Private R2 bytes mismatch');
  const v=c.createVerify('RSA-SHA256');for await(const b of fs.createReadStream(archive))v.update(b);v.end();
  if(!v.verify(key,fs.readFileSync(sig)))throw new Error('Publisher signature invalid');
  run('openssl',['dgst','-sha256','-verify',path.resolve(pem),'-signature',sig,archive]);
  const etag=String(response.ETag||'').replaceAll('"','');if(!/^[0-9a-f]{32}(?:-[1-9][0-9]*)?$/.test(etag))throw new Error('Invalid object ETag');
  const report={format:'tec-regional-r2-readback/v1',...expected,etag,fullObjectReadback:true,publisherSignatureVerified:true,independentVerifier:'OpenSSL dgst -sha256',verifiedAtUtc:new Date().toISOString(),gatewayActivated:false};
  fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log('PASS exact private archive, signature and publisher identity; evidence: '+out);
 } finally {fs.rmSync(tmp,{recursive:true,force:true});}
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
