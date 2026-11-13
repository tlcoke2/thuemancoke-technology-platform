'use strict';
/** TEC EPR Clinic Edition 1.0.1 FRESH INSTALLATIONS ONLY owner release conductor.
 * No publisher key/password/private URL/clinic data leaves the owner workstation.
 * Only --mode release --confirm-owner-release performs signing and private R2 upload.
 * Original 1.0.0 archive, customer installations and Docker volumes are not touched.
 */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const cp=require('node:child_process'),crypto=require('node:crypto');
const RELEASE='1.0.1', SOURCE_BACKEND='91b848bfccb0951e010be8f566b4146a53b6a586';
const SOURCE_FRONTEND='345384515c70dd7f6569e96f5c38b749b4ff986d';
const MANIFEST_SHA='66907861e79d59a463dbb3b0d178bfe5fba3dfb85c8c8347c152e0cbf8f58218';
const IMAGES_SHA='bbd30c1729e5d00219756ba58568ff4643de8e0412252a1c0d8890baca569c20';
const LEGACY_PUBLISHER_SPKI='6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733';
const PUBLISHER_SPKI='b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a';
const BACKEND_HEAD='4db43f051f6a4534955902d81e784b355cadaecf';
const GATEWAY_HEAD='b3e137f75d6e41a5885367efc65025e2823cfbea';
const BACKEND_BRANCH='review/rc5-101-synthetic-image-rehearsal-20261110';
const GATEWAY_BRANCH='release/tec-epr-101-fresh-private-gateway-20261111';
const BUCKET='tec-epr-private-releases';
const ENDPOINT='https://d0ad5986fca56c661b92988f2ea1c1f7.r2.cloudflarestorage.com';
const FRESH='FRESH_INSTALLATIONS_ONLY';
const HEX=/^[0-9a-f]{64}$/;
function hold(ok,reason){if(!ok)throw Error('HOLD_RC5_101_COMMERCIAL_RELEASE: '+reason)}
function sha(b){return crypto.createHash('sha256').update(b).digest('hex')}
async function hashFile(f){const h=crypto.createHash('sha256');for await(const b of fs.createReadStream(f))h.update(b);return h.digest('hex')}
function run(bin,args,{env=process.env,quiet=false,timeout=300000}={}){
 const r=cp.spawnSync(bin,args,{shell:false,encoding:'utf8',windowsHide:true,env,timeout,maxBuffer:8*1024*1024,
  stdio:quiet?['ignore','pipe','pipe']:['ignore','pipe','pipe']});
 if(r.error||r.status!==0)throw Error('HOLD_RC5_101_COMMERCIAL_RELEASE: required local '+bin+' process failed; no credentials or raw program output displayed');
 return r.stdout.trim();
}
function parse(argv){const o={mode:'plan'};let seenMode=false;
 for(let i=0;i<argv.length;i++){
  const x=argv[i];if(x==='--confirm-owner-release'){hold(o.confirm!==true,'Duplicate owner confirmation');o.confirm=true;continue}
  if(x==='--confirm-owner-resume'){hold(o.resumeConfirm!==true,'Duplicate owner resume confirmation');o.resumeConfirm=true;continue}
  const map={'--mode':'mode','--approval':'approval','--private-key':'privateKey','--public-key':'publicKey',
   '--aws-profile':'profile','--rotation-approval':'rotationApproval','--workspace':'workspace','--candidate-stage':'candidateStage'};
  hold(Object.hasOwn(map,x)&&!(map[x]==='mode'?seenMode:Object.hasOwn(o,map[x])),'Unsupported or repeated argument: '+x);
  if(map[x]==='mode')seenMode=true;
  const val=argv[++i];hold(typeof val==='string'&&val&&!val.startsWith('--'),'Missing CLI value: '+x);o[map[x]]=val;
 }
 hold(['plan','release','resume'].includes(o.mode),'Use --mode plan, release or resume');
 hold(o.mode!=='release'||o.confirm===true,'Release requires explicit --confirm-owner-release');
 hold(o.mode!=='resume'||o.resumeConfirm===true,'Resume requires explicit --confirm-owner-resume');
 hold(o.mode!=='resume'||o.confirm!==true,'Resume cannot request new signing');
 return o;
}
function defaultWorkspace(){return path.join(os.homedir(),'TEC-EPR-1.0.1-FRESH-RELEASE-OWNER')}
function template(candidate){return {assertion:'PENDING_REVIEW_REPLACE_ONLY_WITH_VERIFIED_APPROVALS',releaseScope:FRESH,
 releaseVersion:RELEASE,candidateManifestSha256:MANIFEST_SHA,
 source:{backendRevision:SOURCE_BACKEND,frontendRevision:SOURCE_FRONTEND},review:{
  medicalDirector:{approved:false,reviewer:'',approvedAtUtc:'',evidenceReference:''},
  security:{approved:false,reviewer:'',approvedAtUtc:'',evidenceReference:''},
  existingCustomerUpgrade:{approved:false,notApplicable:true,scope:FRESH,reviewer:'',approvedAtUtc:'',evidenceReference:''},
  offHostDR:{approved:false,reviewer:'',approvedAtUtc:'',evidenceReference:''},
  publisher:{approved:false,reviewer:'',approvedAtUtc:'',evidenceReference:''},
  gateway:{approved:false,reviewer:'',approvedAtUtc:'',evidenceReference:''}
 },notes:'This is a template only. Copy documented earlier sign-offs/references accurately. Existing-customer upgrades stay unsupported.'}}
function verifyApproval(approval){hold(approval?.assertion==='APPROVED_FOR_COMMERCIAL_SIGNING'&&
 approval.releaseScope===FRESH&&approval.releaseVersion===RELEASE&&approval.candidateManifestSha256===MANIFEST_SHA&&
 approval.source?.backendRevision===SOURCE_BACKEND&&approval.source?.frontendRevision===SOURCE_FRONTEND,
 'Approval record must bind the actual 1.0.1 candidate and fresh-only scope');
 for(const name of ['medicalDirector','security','existingCustomerUpgrade','offHostDR','publisher','gateway']){
  const x=approval.review?.[name];hold(typeof x?.reviewer==='string'&&x.reviewer.trim().length>=3&&
  typeof x.evidenceReference==='string'&&x.evidenceReference.trim().length>=6&&
  typeof x.approvedAtUtc==='string'&&x.approvedAtUtc.endsWith('Z')&&Number.isFinite(Date.parse(x.approvedAtUtc))&&
  Date.parse(x.approvedAtUtc)<=Date.now()+300000,'Missing real reviewed evidence for '+name);
  if(name==='existingCustomerUpgrade')hold(x.approved===false&&x.notApplicable===true&&x.scope===FRESH,
   'Existing-customer upgrade must be explicitly NOT APPLICABLE for fresh-only release');
  else hold(x.approved===true,'Unapproved release gate: '+name);
 }
 return true;
}
function verifyRotation(approval){
 hold(approval?.kind==='tec-epr-101-publisher-trust-rotation-v1'&&
  approval.decision==='APPROVED_FOR_SIGNING_1_0_1'&&
  approval.releaseVersion===RELEASE&&approval.releaseScope===FRESH&&
  approval.candidateManifestSha256===MANIFEST_SHA&&
  approval.previousPublisherSpkiSha256===LEGACY_PUBLISHER_SPKI&&
  approval.newPublisherSpkiSha256===PUBLISHER_SPKI&&
  approval.legacyVerificationPreserved===true&&
  approval.existingCustomerUpgradeSupported===false&&
  approval.authorizedKeyRotation===true&&
  typeof approval.approvedBy==='string'&&approval.approvedBy.trim().length>=3&&
  typeof approval.evidenceReference==='string'&&approval.evidenceReference.trim().length>=12&&
  typeof approval.approvedAtUtc==='string'&&approval.approvedAtUtc.endsWith('Z')&&
  Number.isFinite(Date.parse(approval.approvedAtUtc))&&
  Date.parse(approval.approvedAtUtc)<=Date.now()+300000,
  'Owner-controlled explicit trust rotation approval missing or mismatched');
 return true;
}
function checkGit(root,ref,shaExpected,remote){
 const folder=path.resolve(root);hold(fs.existsSync(folder),'Missing reviewed source checkout '+ref);
 hold(run('git',['-C',folder,'rev-parse','HEAD'],{quiet:true})===shaExpected,
  'Reviewed signing toolchain source drift for '+ref);
 const configured=run('git',['-C',folder,'remote','get-url','origin'],{quiet:true});
 hold(configured.includes(remote),'Signing checkout Git remote does not match the approved repository');
 return folder;
}
function checkStage(stage){
 const base=path.join(stage,'VERIFIED-CANDIDATE-1.0.1');
 const manifest=path.join(base,'manifest.json');
 const scan=path.join(stage,'rc5-1.0.1-exact-offline-scanner-attestation.json');
 hold(fs.existsSync(manifest)&&fs.existsSync(scan),'Expected previously verified 1.0.1 candidate/scan evidence missing');
 hold(sha(fs.readFileSync(manifest))===MANIFEST_SHA,'Frozen commercial candidate manifest does not match');
 const m=JSON.parse(fs.readFileSync(manifest,'utf8'));
 const a=JSON.parse(fs.readFileSync(scan,'utf8'));
 hold(m.source?.backendRevision===SOURCE_BACKEND&&m.source?.frontendRevision===SOURCE_FRONTEND&&
  m.status==='VALIDATION CANDIDATE — NOT PRODUCTION CERTIFIED'&&m.targetReleaseVersion===RELEASE,
  'Unreviewed candidate source or current release status');
 hold(a.candidateManifestSha256===MANIFEST_SHA&&a.imagesTarSha256===IMAGES_SHA&&
 a.status==='PASSED_PENDING_PUBLISHER_APPROVAL'&&
 Object.keys(a.scanners||{}).sort().join(',')==='backend,database,frontend'&&
 Object.values(a.scanners||{}).every(x=>x==='PASS_ZERO_CRITICAL_HIGH'),
 'Frozen three-image security attestation absent or failed');
 const version=JSON.parse(fs.readFileSync(path.join(base,'schema-version.json'),'utf8'));
 hold(version.upgradeSupported===false&&version.version==='20261109-fresh-v2',
 'Existing-customer upgrade must remain explicitly unsupported');
 return {base,scan};
}
function cloneIfMissing(target,repository,branch,expected){
 if(!fs.existsSync(target)){
  fs.mkdirSync(path.dirname(target),{recursive:true});
  run('git',['clone','--branch',branch,'--single-branch',
   'https://github.com/tlcoke2/'+repository+'.git',target],{timeout:240000});
 }
 checkGit(target,branch,expected,'tlcoke2/'+repository);
}
function makeWork(workspace){fs.mkdirSync(workspace,{recursive:true,mode:0o700});
 const templatePath=path.join(workspace,'APPROVAL-TEMPLATE-FRESH-ONLY-NOT-APPROVED.json');
 if(!fs.existsSync(templatePath))fs.writeFileSync(templatePath,JSON.stringify(template(),null,2)+'\n',{flag:'wx',mode:0o600});
 return templatePath;}
function fileRequirement(file,label){hold(file&&fs.existsSync(file)&&fs.statSync(file).isFile(),label+' file not found');return path.resolve(file)}
function readObject(f){const v=JSON.parse(fs.readFileSync(f,'utf8'));hold(v&&typeof v==='object'&&!Array.isArray(v),'Invalid review JSON');return v}
function outputSafe(p,value){hold(!fs.existsSync(p),'Existing release report must not be replaced');fs.writeFileSync(p,JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600})}
function awsEnv(profile){hold(typeof profile==='string'&&/^[A-Za-z0-9_+=,.@-]{1,100}$/.test(profile),
 'Dedicated owner R2 publisher AWS CLI profile required');
 const env={...process.env,AWS_PROFILE:profile,AWS_EC2_METADATA_DISABLED:'true'};
 for(const k of Object.keys(env))if(/^AWS_(ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN|WEB_IDENTITY_TOKEN_FILE)$/.test(k))delete env[k];
 return env;
}
function aws(args,env){return run('aws',['--no-cli-pager','--endpoint-url',ENDPOINT,'s3api',...args,'--output','json'],{env,timeout:600000,quiet:true})}
async function uploadPrivate({archive,sha256,bytes,profile}){
 const env=awsEnv(profile),key='tec-epr/clinic-edition/1.0.1/'+path.basename(archive);
 // Refuse an existing object even if its ETag happens to match: immutable object policy.
 const head=cp.spawnSync('aws',['--no-cli-pager','--endpoint-url',ENDPOINT,'s3api','head-object',
  '--bucket',BUCKET,'--key',key,'--output','json'],{encoding:'utf8',shell:false,windowsHide:true,env,timeout:60000});
 if(!head.error&&head.status===0)throw Error('HOLD_RC5_101_COMMERCIAL_RELEASE: private R2 object already exists; never overwrite a signed release');
 const msg=String(head.stderr||'');
 hold(!head.error&&/\b404\b|Not Found|NoSuchKey/.test(msg),
  'Cannot independently establish that the private R2 key is absent; check scoped credentials');
 aws(['put-object','--bucket',BUCKET,'--key',key,'--body',archive,
  '--metadata','sha256='+sha256+',release=1.0.1,scope=fresh-only'],env);
 const remote=JSON.parse(aws(['head-object','--bucket',BUCKET,'--key',key],env));
 hold(remote.ContentLength===bytes&&remote.Metadata?.sha256===sha256,
  'Private R2 uploaded object size or immutable SHA metadata differs');
 const etag=String(remote.ETag||'').replace(/^"|"$/g,'');
 hold(/^[a-f0-9]{32}(?:-[1-9][0-9]*)?$/.test(etag),'Invalid R2 ETag metadata');
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'tec-epr-101-r2-readback-'));
 try{
  const target=path.join(temp,'readback.tar.gz');
  aws(['get-object','--bucket',BUCKET,'--key',key,target],env);
  hold(fs.statSync(target).size===bytes&&(await hashFile(target))===sha256,
   'Private R2 full readback differs from signed release; NOT ACTIVATED');
 }finally{fs.rmSync(temp,{recursive:true,force:true})}
 return {key,etag,sha256,bytes};
}
async function perform(o){
 const workspace=path.resolve(o.workspace||defaultWorkspace());const approvalTemplate=makeWork(workspace);
 const stage=path.resolve(o.candidateStage||path.join(os.homedir(),'TEC-EPR-RC5-101-Candidate-Review'));
 const candidate=checkStage(stage);
 const result={releaseVersion:RELEASE,releaseScope:FRESH,
  candidateManifestSha256:MANIFEST_SHA,backendRevision:SOURCE_BACKEND,
  frontendRevision:SOURCE_FRONTEND,archiveSigned:false,r2Uploaded:false,
  privateDownloadEnabled:false,customerLicenseIssued:false,existingCustomerUpgradeSupported:false};
 if(o.mode==='plan'){
  console.log('PASS_RC5_101_OWNER_RELEASE_CANDIDATE_IDENTIFIED');
  console.log('Approval evidence template: '+approvalTemplate);
  console.log('HOLD: plan is read-only; choose --mode release with authentic approval records and owner-controlled private key.');
  return result;
 }
 const approvalFile=fileRequirement(o.approval||process.env.TEC_101_APPROVAL_JSON,'Owner 1.0.1 approval JSON');
 const rotationApprovalFile=fileRequirement(o.rotationApproval||process.env.TEC_101_ROTATION_APPROVAL_JSON,
  'New 1.0.1 publisher trust rotation authorisation');
 const privateKey=o.mode==='resume'?null:fileRequirement(o.privateKey||process.env.TEC_PUBLISHER_PRIVATE_KEY_PATH,'Offline publisher private key');
 const publicKey=fileRequirement(o.publicKey||process.env.TEC_PUBLISHER_TRUSTED_PUBLIC_KEY_PATH,'Independently trusted publisher public key');
 const approval=readObject(approvalFile);verifyApproval(approval);
 const rotationRaw=fs.readFileSync(rotationApprovalFile);
 hold(rotationRaw.length<65536,'Publisher rotation authorisation too large');
 verifyRotation(JSON.parse(rotationRaw.toString('utf8')));
 console.log('PASS_RC5_101_EXPLICIT_ROTATED_PUBLISHER_TRUST_APPROVED');
 const backendDir=path.join(workspace,'reviewed-backend');const gatewayDir=path.join(workspace,'reviewed-gateway');
 cloneIfMissing(backendDir,'tec_epr_backend',BACKEND_BRANCH,BACKEND_HEAD);
 cloneIfMissing(gatewayDir,'thuemancoke-technology-platform',GATEWAY_BRANCH,GATEWAY_HEAD);
 const backendFinalizer=require(path.join(backendDir,'scripts','rc5-finalize-publisher-release.cjs'));
 const backendVerify=require(path.join(backendDir,'scripts','rc5-verify-publisher-release.cjs'));
 const fingerprint=backendFinalizer.PINNED_PUBLISHER_SPKI_SHA256;
 hold(fingerprint===PUBLISHER_SPKI&&
  backendFinalizer.LEGACY_100_PUBLISHER_SPKI_SHA256===LEGACY_PUBLISHER_SPKI,
  'Unapproved 1.0.1 publisher identity or missing historical 1.0.0 verification anchor');
 const publicObj=crypto.createPublicKey(fs.readFileSync(publicKey));
 hold(sha(publicObj.export({format:'der',type:'spki'}))===PUBLISHER_SPKI,
  'Trusted publisher public verification key fingerprint mismatch');
 const outputDir=path.join(workspace,'SIGNED-1.0.1-RELEASE');fs.mkdirSync(outputDir,{recursive:true});
 const output=path.join(outputDir,'TEC-EPR-Clinic-Edition-1.0.1-fresh-'+MANIFEST_SHA.slice(0,12)+'.tar.gz');
 if(o.mode==='resume'){
  hold(fs.existsSync(output)&&fs.statSync(output).isFile()&&
    fs.existsSync(output+'.release-evidence.json')&&fs.existsSync(output+'.sha256'),
    'Resume requires EXISTING signed archive and BOTH immutable evidence sidecars');
 }else{
  hold(!fs.existsSync(output),'Immutable signed 1.0.1 output already exists; do not re-sign or overwrite');
 }
 let signed;
 if(o.mode==='resume'){
  // Controlled one-way continuation from the SAME owner-signed archive.
  // Never read a private PEM/passphrase; never call seal; never change the archive.
  signed=readObject(output+'.release-evidence.json');
  hold(signed.status==='SIGNED_PENDING_COMMERCIAL_GATEWAY_APPROVAL'&&
    signed.releaseVersion===RELEASE&&signed.releaseScope===FRESH&&
    signed.upgradeSupported===false&&signed.gatewayActivated===false&&
    signed.archiveFilename===path.basename(output)&&
    HEX.test(signed.archiveSha256||'')&&
    signed.publisherSpkiSha256===PUBLISHER_SPKI&&
    signed.previousPublisherSpkiSha256===LEGACY_PUBLISHER_SPKI&&
    signed.publisherTrustRotationApprovalSha256===sha(rotationRaw)&&
    signed.source?.backendRevision===SOURCE_BACKEND&&
    signed.source?.frontendRevision===SOURCE_FRONTEND&&
    signed.imageIds&&Object.keys(signed.imageIds).sort().join(',')==='backend,database,frontend',
    'Cannot resume release with unsigned, unreviewed or mismatched 1.0.1 evidence');
  hold(signed.archiveBytes===fs.statSync(output).size&&
    (await hashFile(output))===signed.archiveSha256,
    'Existing signed archive differs from its SHA256/byte evidence');
  const sidecar=fs.readFileSync(output+'.sha256','utf8').trim();
  hold(sidecar===signed.archiveSha256+'  '+path.basename(output),
    'Existing immutable .sha256 sidecar does not match signed archive');
  console.log('PASS_RC5_101_EXISTING_SIGNED_ARCHIVE_REUSED_WITHOUT_RESIGNING');
 }else{
  const passphraseFile=process.env.TEC_PUBLISHER_KEY_PASSPHRASE_FILE;
  if(passphraseFile)fileRequirement(passphraseFile,'Protected publisher passphrase');
  console.log('STAGE_RC5_101_SIGNING_NEW_RSA4096_TRUST_ROTATION');
  signed=await backendFinalizer.seal({candidateDir:candidate.base,approvalFile,
   scanEvidencePath:candidate.scan,privateKeyPath:privateKey,outputPath:output,
   rotationApprovalFile,
   ...(passphraseFile?{passphraseFile:path.resolve(passphraseFile)}:{})});
 }
 console.log('STAGE_RC5_101_INDEPENDENT_RSA_ARCHIVE_VERIFICATION');
 const independently=await backendVerify.verify(output,publicKey).catch(e=>{
  throw Error('HOLD_RC5_101_COMMERCIAL_RELEASE: independent RSA archive verifier: '+e.message);
 });
 hold(independently.assessment==='PASS_SIGNED_COMMERCIAL_ARCHIVE_AUTHENTICITY_AND_CONTENTS'&&
  independently.archiveSha256===signed.archiveSha256&&independently.publisherSpkiSha256===PUBLISHER_SPKI&&
  independently.publisherTrustRotationApprovalSha256===sha(rotationRaw)&&
  independently.previousPublisherSpkiSha256===LEGACY_PUBLISHER_SPKI,
  'Independent signed release verifier refused downloaded archive');
 result.archiveSigned=true;result.archiveSha256=signed.archiveSha256;result.archiveBytes=signed.archiveBytes;
 result.signedArchivePath=output;
 console.log('PASS_RC5_101_PUBLISHER_RSA4096_SIGNED_AND_INDEPENDENTLY_VERIFIED');
 // Independently validate with the private gateway's full signed-payload verifier.
 const trustDir=path.join(workspace,'TRUST-101-CONTROLS');
 hold(!fs.existsSync(trustDir),'External verification workspace already exists; preserve prior evidence');
 fs.mkdirSync(trustDir,{recursive:false});
 run('tar',['-xzf',output,'-C',trustDir,'./manifest.json','./manifest.sig','./manifest.signer.json'],{timeout:120000});
 const reportPath=path.join(workspace,'RELEASE-101-INDEPENDENT-VERIFICATION.json');
 const gatewayVerifier=path.join(gatewayDir,'customer_gateway','verify_release_101.py');
 console.log('STAGE_RC5_101_INDEPENDENT_GATEWAY_VERIFICATION');
 run('python',[gatewayVerifier,'--release-dir',trustDir,'--public-key',publicKey,
  '--archive',output,'--release-evidence',output+'.release-evidence.json',
  '--report-json',reportPath],{timeout:600000});
 const verified=readObject(reportPath);
 hold(verified.assessment==='VERIFIED_1_0_1_ARCHIVE_PENDING_HUMAN_GATEWAY_APPROVAL'&&
  verified.publisherSignatureVerified===true&&verified.allArchiveMembersVerified===true&&
  verified.verifiedArchiveSha256===signed.archiveSha256&&verified.releaseScope===FRESH&&
  verified.upgradeSupported===false&&
  verified.publisherSpkiSha256===PUBLISHER_SPKI&&
  verified.previousPublisherSpkiSha256===LEGACY_PUBLISHER_SPKI&&
  verified.publisherTrustRotationApprovalSha256===sha(rotationRaw),
  'Independent private gateway release verification failed');
 console.log('PASS_RC5_101_INDEPENDENT_GATEWAY_SIGNATURE_AND_PAYLOAD_REVIEW');
 const releaseMetadata=readObject(output+'.release-evidence.json');
 console.log('STAGE_RC5_101_PRIVATE_R2_PUBLICATION_AND_READBACK');
 const remote=await uploadPrivate({archive:output,sha256:signed.archiveSha256,bytes:signed.archiveBytes,
  profile:o.profile||process.env.TEC_R2_PUBLISH_PROFILE});
 result.r2Uploaded=true;result.r2Key=remote.key;
 console.log('PASS_RC5_101_PRIVATE_R2_FULL_SHA256_READBACK');
 // Create nonsecret audit handoff only. Do not set Railway variables or flip
 // release switches on from an owner workstation without production change review.
 const config={format:'tec-epr-101-private-commercial-activation-v1',
  releaseScope:FRESH,releaseVersion:RELEASE,privateBucket:BUCKET,privateObjectKey:remote.key,
  GATEWAY_RELEASE_ID:'tec-epr-clinic-1.0.1',
  publisherSpkiSha256:PUBLISHER_SPKI,
  previousPublisherSpkiSha256:LEGACY_PUBLISHER_SPKI,
  publisherTrustRotationApprovalSha256:sha(rotationRaw),
  GATEWAY_SIGNED_101_RELEASE_EVIDENCE_JSON:JSON.stringify(releaseMetadata),
  GATEWAY_VERIFIED_101_REPORT_JSON:JSON.stringify(verified),
  GATEWAY_R2_101_EXPECTED_ETAG:remote.etag,
  GATEWAY_R2_101_READBACK_SHA256:remote.sha256,
  GATEWAY_MEDICAL_RELEASE_APPROVAL_REF:approval.review.medicalDirector.evidenceReference,
  GATEWAY_OWNER_COMMERCIAL_APPROVAL_REF:approval.review.gateway.evidenceReference,
  GATEWAY_DOWNLOADS_ENABLED:'false',GATEWAY_RELEASE_APPROVED:'false',
  requiresProductionGatewayAndWorkOSMfa:true,customerAccessNotYetGranted:true};
 const configPath=path.join(workspace,'PRIVATE-GATEWAY-101-ACTIVATION-HANDOFF.json');
 outputSafe(configPath,config);
 result.handoffPath=configPath;
 console.log('PASS_RC5_101_SIGNED_PRIVATE_DISTRIBUTION_HANDOFF_READY');
 console.log('HOLD: Gateway release/download flags remain OFF until approved production gateway rollout.');
 console.log('Nonsecret activation handoff path: '+configPath);
 return result;
}
async function main(){try{
 const options=parse(process.argv.slice(2));
 await perform(options);
}catch(e){console.error(e.message.startsWith('HOLD_RC5_101')?e.message:
 'HOLD_RC5_101_COMMERCIAL_RELEASE: failed; no gateway or customer downloads enabled.');process.exitCode=2}}
if(require.main===module)main();
module.exports={parse,template,verifyApproval,verifyRotation,checkStage,awsEnv,FRESH,MANIFEST_SHA};