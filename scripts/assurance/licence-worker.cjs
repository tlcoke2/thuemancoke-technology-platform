'use strict';
// Local-only signer. No network listener, production key or credentials included.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');
const MODULES = new Set('patients users admin facilities appointments billing discharges lab medicines prescriptions pricing procedurecodes qc settings specimens tasks treatments uploads lims ai export labintegration codes availability instruments'.split(' '));
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function pin(key) { return crypto.createHash('sha256').update(crypto.createPublicKey(key).export({type:'spki',format:'der'})).digest('hex'); }
function publicPin(key) { return crypto.createHash('sha256').update(key.export({type:'spki',format:'der'})).digest('hex'); }
function ensurePin(actual, expected) { if (!/^[a-f0-9]{64}$/.test(expected || '') || actual !== expected) throw new Error('Trusted key fingerprint mismatch'); }
function parseEnvelope(bytes, approvalPublicPem, approvalPin) {
  if (!Buffer.isBuffer(bytes) || bytes.length > 16384) throw new Error('Bounded approval envelope required');
  const key = crypto.createPublicKey(approvalPublicPem);
  if (key.asymmetricKeyType !== 'rsa' || key.asymmetricKeyDetails.modulusLength < 4096) throw new Error('RSA-4096 approval key required');
  ensurePin(publicPin(key), approvalPin);
  const envelope = JSON.parse(bytes.toString('utf8'));
  if (!envelope || Object.keys(envelope).sort().join(',') !== 'job,signature' || typeof envelope.signature !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(envelope.signature)) throw new Error('Invalid approval envelope');
  const job = envelope.job;
  const serialized = JSON.stringify(job);
  if (!crypto.verify('RSA-SHA256', Buffer.from(serialized), key, Buffer.from(envelope.signature,'base64'))) throw new Error('Approval signature invalid');
  const fields = 'approvalExpiresAt,approvalId,approvedAt,customerName,expiresAt,installationId,jobId,licencePublicKeySha256,modules,version';
  if (!job || Object.keys(job).sort().join(',') !== fields || job.version !== 1 || !UUID.test(job.jobId) || !UUID.test(job.approvalId) || !UUID.test(job.installationId)) throw new Error('Invalid approved job identity');
  if (typeof job.customerName !== 'string' || !job.customerName.trim() || job.customerName.length > 200 || /[\x00-\x1f\x7f]/.test(job.customerName)) throw new Error('Invalid organisation');
  if (!Array.isArray(job.modules) || !job.modules.length || job.modules.length > 25 || new Set(job.modules).size !== job.modules.length || job.modules.some(x => x !== '*' && !MODULES.has(x)) || (job.modules.includes('*') && job.modules.length !== 1)) throw new Error('Invalid approved modules');
  for (const field of ['approvedAt','approvalExpiresAt','expiresAt']) {
    if (typeof job[field] !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$/.test(job[field]) || !Number.isFinite(Date.parse(job[field]))) throw new Error('Explicit UTC dates required');
    if (new Date(job[field]).toISOString().replace(/\.000Z$/, 'Z') !== job[field].replace(/\.000Z$/, 'Z')) throw new Error('Invalid calendar date');
  }
  if (!/^[a-f0-9]{64}$/.test(job.licencePublicKeySha256 || '')) throw new Error('Approved licence key fingerprint required');
  const start = Date.parse(job.approvedAt), end = Date.parse(job.approvalExpiresAt);
  if (end <= start || end - start > 24*3600*1000 || Date.parse(job.expiresAt) <= start) throw new Error('Approval validity invalid');
  return {job, hash:crypto.createHash('sha256').update(serialized).digest('hex')};
}
function verifyLicence(encoded, key, job) {
  const envelope=JSON.parse(Buffer.from(encoded,'base64').toString('utf8'));
  if (!crypto.verify('RSA-SHA256',Buffer.from(JSON.stringify(envelope.payload)),key,Buffer.from(envelope.signature,'base64'))) throw new Error('Persisted licence signature invalid');
  const p=envelope.payload;
  if (p.version!==1 || p.customerName!==job.customerName || p.installationId!==job.installationId || p.expiresAt!==job.expiresAt || JSON.stringify(p.modules)!==JSON.stringify(job.modules)) throw new Error('Persisted claims mismatch');
  return p;
}
function issue(options) {
  const {job,hash}=parseEnvelope(options.approvalBytes,options.approvalPublicPem,options.approvalPin);
  if (!/-----BEGIN ENCRYPTED PRIVATE KEY-----/.test(options.signingPem.toString())) throw new Error('Encrypted PKCS8 signing key required');
  const key=crypto.createPrivateKey({key:options.signingPem,passphrase:options.passphrase});
  if (key.asymmetricKeyType!=='rsa' || key.asymmetricKeyDetails.modulusLength<4096) throw new Error('RSA-4096 licence key required');
  ensurePin(pin(key),options.signingPin);
  ensurePin(options.signingPin,job.licencePublicKeySha256);
  const publicKey=crypto.createPublicKey(key);
  const now=options.now === undefined ? Date.now() : options.now;
  if (Date.parse(job.approvedAt)>now || Date.parse(job.expiresAt)<=now) throw new Error('Job not yet approved or licence expired');
  const parent=path.dirname(path.resolve(options.dbPath));
  if (!fs.existsSync(parent)) fs.mkdirSync(parent,{recursive:true,mode:0o700});
  if (process.platform!=='win32' && (fs.statSync(parent).mode & 0o077)) throw new Error('Ledger directory must be private (0700)');
  const fd=fs.openSync(options.dbPath,'a',0o600);fs.closeSync(fd);
  if (process.platform!=='win32' && (fs.statSync(options.dbPath).mode & 0o077)) throw new Error('Ledger file must be private (0600)');
  const db=new DatabaseSync(options.dbPath);
  try {
    db.exec('PRAGMA busy_timeout=5000; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS issuance(job_id TEXT PRIMARY KEY, approval_id TEXT UNIQUE NOT NULL, job_hash TEXT NOT NULL, signing_pin TEXT NOT NULL, licence TEXT NOT NULL, issued_at TEXT NOT NULL) STRICT; BEGIN IMMEDIATE;');
    const old=db.prepare('SELECT * FROM issuance WHERE job_id=?').get(job.jobId);
    if (old) {
      if (old.job_hash!==hash || old.signing_pin!==options.signingPin) throw new Error('Job ID replay with changed approved claims or key');
      const payload=verifyLicence(old.licence,publicKey,job);
      db.exec('COMMIT');
      return {licence:old.licence,licenseId:payload.licenseId,reused:true};
    }
    if (Date.parse(job.approvalExpiresAt)<=now) throw new Error('Approval expired before first issuance');
    const payload={version:1,licenseId:crypto.randomUUID(),customerName:job.customerName,installationId:job.installationId,issuedAt:new Date(now).toISOString(),expiresAt:job.expiresAt,modules:job.modules};
    const signature=crypto.sign('RSA-SHA256',Buffer.from(JSON.stringify(payload)),key).toString('base64');
    const licence=Buffer.from(JSON.stringify({payload,signature})).toString('base64');
    verifyLicence(licence,publicKey,job);
    db.prepare('INSERT INTO issuance VALUES(?,?,?,?,?,?)').run(job.jobId,job.approvalId,hash,options.signingPin,licence,payload.issuedAt);
    db.exec('COMMIT');
    return {licence,licenseId:payload.licenseId,reused:false};
  } catch(error) {
    try { db.exec('ROLLBACK'); } catch {}
    throw error;
  } finally { db.close(); }
}
function saveOutput(filename, licence) {
  if (fs.existsSync(filename)) {
    if (fs.readFileSync(filename,'utf8')!==licence+'\n') throw new Error('Output exists with different contents');
    return;
  }
  fs.writeFileSync(filename,licence+'\n',{flag:'wx',mode:0o600});
}
function readPassphrase() {
  if (!process.stdin.isTTY) throw new Error('Interactive terminal required; passphrases cannot be piped');
  process.stdout.write('Signing-key passphrase: ');
  process.stdin.setRawMode(true);process.stdin.resume();
  return new Promise((resolve,reject)=>{
    const bytes=[];
    function finish(error) {
      process.stdin.off('data',onData);process.stdin.setRawMode(false);process.stdin.pause();process.stdout.write('\n');
      if(error) { bytes.fill(0);reject(error); } else { const result=Buffer.from(bytes);bytes.fill(0);resolve(result); }
    }
    function onData(data) {
      for(const byte of data) {
        if(byte===3) return finish(new Error('Cancelled'));
        if(byte===13 || byte===10) return finish();
        if(byte===127 || byte===8) bytes.pop();
        else if(bytes.length<4096) bytes.push(byte);
        else return finish(new Error('Passphrase too long'));
      }
    }
    process.stdin.on('data',onData);
  });
}
module.exports={issue,parseEnvelope,saveOutput,pin};
if(require.main===module) (async()=>{
  if(process.argv.length!==4) throw new Error('Usage: node licence-worker.cjs trusted-local-config.json approved-job.json');
  const config=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
  if(config.commissioned!==true) throw new Error('Local signer commissioning required');
  if(fs.statSync(process.argv[3]).size>16384) throw new Error('Approval envelope too large');
  const approvalBytes=fs.readFileSync(process.argv[3]);
  if(approvalBytes.length>16384) throw new Error('Approval envelope too large');
  // Validate approval before prompting for key unlock.
  const approvalPublicPem=fs.readFileSync(config.approvalPublicKey);
  parseEnvelope(approvalBytes,approvalPublicPem,config.approvalPin);
  const passphrase=await readPassphrase();
  try {
    const result=issue({approvalBytes,approvalPublicPem,approvalPin:config.approvalPin,signingPem:fs.readFileSync(config.encryptedSigningKey),signingPin:config.signingPin,passphrase,dbPath:config.ledger});
    const job=JSON.parse(approvalBytes).job;
    saveOutput(path.join(config.outputDirectory,job.jobId+'.teclicense'),result.licence);
    console.log(JSON.stringify({licenseId:result.licenseId,reused:result.reused,delivery:'Saved locally; no customer transmission performed'}));
  } finally { passphrase.fill(0); }
})().catch(error=>{console.error(error.message);process.exitCode=1;});
