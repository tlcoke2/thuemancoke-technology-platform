'use strict';
/**
 * Owner-only, LOCAL publisher trust-rotation authorisation for TEC EPR 1.0.1.
 * Does not sign software, read encrypted private material, generate credentials,
 * change production services, or grant customer downloads.
 * Not a cryptographic signature: explicit owner decision and record of new trust.
 */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const crypto=require('node:crypto'),readline=require('node:readline/promises');
const LEGACY='6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733';
const NEW='b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a';
const CANDIDATE='66907861e79d59a463dbb3b0d178bfe5fba3dfb85c8c8347c152e0cbf8f58218';
const DIR='C:\\My_Applications\\TEC-EPR-Publisher-Keys-1.0.1-ROTATED';
const LEGACY_FILE='C:\\My_Applications\\TEC-EPR-Publisher-Trust\\publisher-public-1.0.0.pem';
const OUTPUT=path.join(os.homedir(),'TEC-EPR-1.0.1-FRESH-RELEASE-OWNER','ROTATED-PUBLISHER-TRUST-1.0.1-OWNER-APPROVED.json');
function publicFingerprint(file,expected){
 const key=crypto.createPublicKey(fs.readFileSync(file));
 if(key.asymmetricKeyType!=='rsa'||key.asymmetricKeyDetails?.modulusLength!==4096)
  throw Error('Expected independently trusted RSA-4096 PUBLIC PEM key');
 const fp=crypto.createHash('sha256').update(key.export({type:'spki',format:'der'})).digest('hex');
 if(fp!==expected)throw Error('PUBLIC PEM does not match pinned owner-created publisher identity');
 return fp;
}
async function main(){
 if(process.platform!=='win32'||!process.stdin.isTTY)throw Error('Interactive Windows owner terminal required');
 if(fs.existsSync(OUTPUT))throw Error('Owner trust-rotation approval already exists; preserve and review it; never overwrite');
 const newPub=path.join(DIR,'public.pem');
 publicFingerprint(LEGACY_FILE,LEGACY);
 publicFingerprint(newPub,NEW);
 const priv=fs.statSync(path.join(DIR,'private.pem'));
 if(!priv.isFile())throw Error('Missing rotated encrypted private key (never send it to anyone)');
 console.log('PASS_LEGACY_1_0_0_TRUST_RETAINED');
 console.log('PASS_NEW_1_0_1_RSA4096_PUBLIC_KEY_PINNED');
 console.log('Original clinical candidate: '+CANDIDATE);
 console.log('New 1.0.1 public fingerprint: '+NEW);
 console.log('This changes ONLY 1.0.1 publisher verification. Original 1.0.0 archives remain under legacy trust.');
 console.log('Existing-customer upgrades remain unsupported. Customer downloads will remain OFF.');
 const rl=readline.createInterface({input:process.stdin,output:process.stdout});
 try{
  const name=(await rl.question('Responsible owner / reviewer full name: ')).trim();
  if(name.length<3||name.length>120)throw Error('Real owner reviewer name required');
  const ok=(await rl.question('To authorise THIS NEW key for fresh-only 1.0.1, type APPROVE-ROTATED-101: ')).trim();
  if(ok!=='APPROVE-ROTATED-101')throw Error('Owner trust-rotation authorisation not given');
  const approvedAtUtc=new Date().toISOString();
  const reference='OWNER-ROTATION-101-'+approvedAtUtc.replace(/[-:.TZ]/g,'').slice(0,14);
  const record={
   kind:'tec-epr-101-publisher-trust-rotation-v1',
   decision:'APPROVED_FOR_SIGNING_1_0_1',
   releaseVersion:'1.0.1',releaseScope:'FRESH_INSTALLATIONS_ONLY',
   candidateManifestSha256:CANDIDATE,
   previousPublisherSpkiSha256:LEGACY,
   newPublisherSpkiSha256:NEW,
   legacyVerificationPreserved:true,
   existingCustomerUpgradeSupported:false,
   authorizedKeyRotation:true,
   approvedBy:name,approvedAtUtc,evidenceReference:reference,
   reason:'Owner cannot recover original encrypted publisher-key passphrase. New independent RSA-4096 publisher trust is specifically approved for fresh-only 1.0.1.',
   limitations:'Owner-attested governance record, NOT independently countersigned; production download activation requires separate release and gateway approval.'
  };
  fs.mkdirSync(path.dirname(OUTPUT),{recursive:true});
  fs.writeFileSync(OUTPUT,JSON.stringify(record,null,2)+'\n',{flag:'wx',mode:0o600});
  const saved=JSON.parse(fs.readFileSync(OUTPUT,'utf8'));
  if(saved.newPublisherSpkiSha256!==NEW||saved.decision!==record.decision)throw Error('Saved approval verification failed');
  console.log('PASS_RC5_101_OWNER_ROTATED_PUBLISHER_TRUST_RECORD_SAVED');
  console.log('APPROVAL_RECORD_PATH: '+OUTPUT);
  console.log('PUBLIC_APPROVAL_REFERENCE: '+reference);
  console.log('No private keys, passphrases or customer data were accessed, stored or published.');
 }finally{rl.close()}
}
main().catch(e=>{console.error('HOLD_ROTATION_APPROVAL: '+(e?.message||'Unknown error'));process.exitCode=2});
