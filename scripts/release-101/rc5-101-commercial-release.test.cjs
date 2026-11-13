'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const m=require('./rc5-101-commercial-release.cjs');
function reviewed(){const x=m.template();x.assertion='APPROVED_FOR_COMMERCIAL_SIGNING';
 for(const [name,item] of Object.entries(x.review)){
  item.reviewer='Documented TEC clinician/owner';item.evidenceReference='OWNER-REVIEW-'+name+'-20261111';
  item.approvedAtUtc='2026-11-11T06:00:00Z';
  if(name!=='existingCustomerUpgrade')item.approved=true;
 }return x;}
function reviewedRotation(){return {
 kind:'tec-epr-101-publisher-trust-rotation-v1',decision:'APPROVED_FOR_SIGNING_1_0_1',
 releaseVersion:'1.0.1',releaseScope:'FRESH_INSTALLATIONS_ONLY',
 candidateManifestSha256:m.MANIFEST_SHA,
 previousPublisherSpkiSha256:'6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733',
 newPublisherSpkiSha256:'b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a',
 legacyVerificationPreserved:true,existingCustomerUpgradeSupported:false,authorizedKeyRotation:true,
 approvedBy:'SYNTHETIC CI OWNER',approvedAtUtc:'2026-11-13T16:00:00Z',
 evidenceReference:'SYNTHETIC-CI-APPROVAL-NOT-REAL'
};}
test('owner release cannot start without explicit opt in',()=>{
 assert.equal(m.parse([]).mode,'plan');
 assert.throws(()=>m.parse(['--mode','release']),/explicit --confirm-owner-release/);
 assert.equal(m.parse(['--mode','release','--confirm-owner-release']).mode,'release');
 assert.equal(m.parse(['--mode','release','--confirm-owner-release','--rotation-approval','owner-rotation.json']).rotationApproval,'owner-rotation.json');
 assert.throws(()=>m.parse(['--mode','release','--confirm-owner-release','--confirm-owner-release']),/Duplicate owner confirmation/);
 assert.throws(()=>m.parse(['--mode','release','--unknown','yes']),/Unsupported/);
 assert.throws(()=>m.parse(['--mode','plan','--mode','release']),/Unsupported or repeated/);
});
test('new signer trust rotation requires owner-approved metadata and new key fingerprint',()=>{
 assert.equal(m.verifyRotation(reviewedRotation()),true);
 for(const mutate of [
  x=>x.newPublisherSpkiSha256=x.previousPublisherSpkiSha256,
  x=>x.authorizedKeyRotation=false,
  x=>x.releaseScope='EXISTING_CUSTOMER_UPGRADE',
  x=>x.previousPublisherSpkiSha256='0'.repeat(64),
  x=>x.candidateManifestSha256='0'.repeat(64),
  x=>x.approvedBy='',
  x=>x.evidenceReference='',
  x=>x.approvedAtUtc='2036-11-13T16:00:00Z']){
  const r=reviewedRotation();mutate(r);
  assert.throws(()=>m.verifyRotation(r),/trust rotation approval/);
 }
});
test('release template is not a fabricated approval',()=>{
 const x=m.template();assert.notEqual(x.assertion,'APPROVED_FOR_COMMERCIAL_SIGNING');
 assert.equal(x.review.medicalDirector.approved,false);
 assert.equal(x.review.existingCustomerUpgrade.approved,false);
 assert.equal(x.review.existingCustomerUpgrade.notApplicable,true);
});
test('genuine evidence with fresh-only N/A instead of false upgrade approval passes',()=>{
 assert.equal(m.verifyApproval(reviewed()),true);
});
test('any false commercial or medical approval is a hard HOLD',()=>{
 for(const k of ['medicalDirector','security','offHostDR','publisher','gateway']){
  const x=reviewed();x.review[k].approved=false;
  assert.throws(()=>m.verifyApproval(x),/Unapproved release gate/);
 }
});
test('upgrades cannot be certified in fresh-only package',()=>{
 for(const val of [{approved:true},{notApplicable:false},{scope:'UPGRADE_ALLOWED'}]){
  const x=reviewed();Object.assign(x.review.existingCustomerUpgrade,val);
  assert.throws(()=>m.verifyApproval(x),/Existing-customer upgrade must be explicitly NOT APPLICABLE/);
 }
});
test('wrong source candidate or missing concrete evidence refuses signing',()=>{
 for(const mutate of [x=>x.releaseVersion='1.0.0',x=>x.candidateManifestSha256='0'.repeat(64),
   x=>x.source.backendRevision='wrong',x=>x.releaseScope='UPGRADE_ALLOWED']){
  const x=reviewed();mutate(x);assert.throws(()=>m.verifyApproval(x),/Approval record must bind/);
 }
 const x=reviewed();x.review.medicalDirector.evidenceReference='';
 assert.throws(()=>m.verifyApproval(x),/Missing real reviewed evidence/);
});
test('AWS publisher profile must be explicit; no environment keys exported',()=>{
 assert.throws(()=>m.awsEnv(undefined),/publisher AWS CLI profile/);
 assert.throws(()=>m.awsEnv('bad profile with spaces'),/publisher AWS CLI profile/);
 const before=process.env.AWS_SECRET_ACCESS_KEY;
 try{
  process.env.AWS_SECRET_ACCESS_KEY='SYNTHETIC-ONLY-KEY';
  const e=m.awsEnv('tec-epr-owner-r2');
  assert.equal(e.AWS_PROFILE,'tec-epr-owner-r2');
  assert.equal(e.AWS_SECRET_ACCESS_KEY,undefined);
 }finally{
  if(before===undefined)delete process.env.AWS_SECRET_ACCESS_KEY;
  else process.env.AWS_SECRET_ACCESS_KEY=before;
 }
});
test('owner publisher passphrase variable is resolved only from protected environment, not CLI',()=>{
 const fs=require('node:fs');const path=require('node:path');
 const code=fs.readFileSync(path.join(__dirname,'rc5-101-commercial-release.cjs'),'utf8');
 assert.match(code,/const passphraseFile=process\.env\.TEC_PUBLISHER_KEY_PASSPHRASE_FILE;/);
 assert.doesNotMatch(code,/'--passphrase'/);
});
