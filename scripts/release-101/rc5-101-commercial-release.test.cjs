'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const m=require('./rc5-101-commercial-release.cjs');
function reviewed(){const x=m.template();x.assertion='APPROVED_FOR_COMMERCIAL_SIGNING';
 for(const [name,item] of Object.entries(x.review)){
  item.reviewer='Documented TEC clinician/owner';item.evidenceReference='OWNER-REVIEW-'+name+'-20261111';
  item.approvedAtUtc='2026-11-11T06:00:00Z';
  if(name!=='existingCustomerUpgrade')item.approved=true;
 }return x;}
test('owner release cannot start without explicit opt in',()=>{
 assert.equal(m.parse([]).mode,'plan');
 assert.throws(()=>m.parse(['--mode','release']),/explicit --confirm-owner-release/);
 assert.equal(m.parse(['--mode','release','--confirm-owner-release']).mode,'release');
 assert.throws(()=>m.parse(['--mode','release','--confirm-owner-release','--confirm-owner-release']),/Duplicate owner confirmation/);
 assert.throws(()=>m.parse(['--mode','release','--unknown','yes']),/Unsupported/);
 assert.throws(()=>m.parse(['--mode','plan','--mode','release']),/Unsupported or repeated/);
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