# Protected local licence worker — implementation and commissioning

Status: implemented and fixture-tested; **not commissioned for production**.
Requires Node.js 24 with `node:sqlite`. This is an owner-side command-line worker,
not a customer GUI, an internet service or unattended delivery integration.
The existing manual/desktop issuer remains available during commissioning.

## Implemented controls

- A separate RSA-4096 approval signature is required over the exact JSON job.
  Both approval and licence public keys are pinned by SPKI SHA-256.
- Encrypted PKCS8 licence key only; hidden interactive local passphrase prompt.
  No passphrase argument, environment variable, network listener or key upload.
- Exact job fields, UUIDv4 identifiers, bounded organisation/modules, explicit UTC
  validity and a maximum 24-hour approval window before first issuance.
- Approved job binds the installation, customer, modules, expiry and licence-key
  fingerprint. An approval signer must enforce the real two-person business
  approval before signing; merely naming an approver in customer input is unsafe.
- SQLite immediate transaction, full synchronous writes, unique job and approval
  IDs, canonical job hash and independent signature verification of the result.
- Retry/restart returns the same persisted licence. Changed claims under an existing
  job ID are rejected. A changed approval cannot silently replace a prior licence.
- Save-to-file occurs after durable commit. Delivery can be retried without a new
  signature; an existing different output is never overwritten. No customer email
  or portal delivery is attempted by this worker.

## Approval envelope contract

An authenticated approval adapter must obtain the established independent approval
and sign `Buffer.from(JSON.stringify(job))` with RSA-SHA256. Envelope:
`{"job":{...},"signature":"base64 RSA signature"}`. Exact job fields:

| Field | Meaning |
| --- | --- |
| version | 1 |
| jobId | Unique UUIDv4 used for idempotence |
| approvalId | Unique UUIDv4 bound to the actual approval record |
| installationId | Customer installation UUIDv4 from request JSON |
| customerName | Approved organisation, maximum 200 characters |
| licencePublicKeySha256 | Pinned licence-verification key fingerprint |
| modules | Explicit permitted module list or an expressly approved single `*` |
| approvedAt | UTC timestamp of actual approval |
| approvalExpiresAt | UTC timestamp, no more than 24 hours after approval |
| expiresAt | Approved customer licence UTC expiry |

Do not let the customer create this signed envelope. Do not use the licence private
key as the approval key. The signature asserts trust in a separately commissioned
approval authority; this implementation does not itself appoint that authority or
verify human MFA. The authenticated queue adapter and approval-key protection are
still required before automatic use.

## Trusted local configuration

Keep configuration, ledger directory, output and keys in an owner-only location;
never in a customer package, public repository or shared Downloads directory.
Set Windows ACLs to the specific operator/service identity; validate them during
commissioning. POSIX private directory/file modes are checked by the worker.
Windows ACL enforcement is a required commissioning control, not proven here.

Configuration keys: `commissioned` (false until acceptance), `approvalPublicKey`,
`approvalPin`, `encryptedSigningKey`, `signingPin`, `ledger`, `outputDirectory`.
Paths are trusted absolute local paths. The output directory must already exist.
Production `signingPin` must match the approved existing key:
`feba748a1b088c114f0e63e49d28b6203ca7d28c0b72e75aace3511379342f26`.
Never generate a replacement production licence key as a workaround.

Once commissioned:

```
node scripts/assurance/licence-worker.cjs trusted-local-config.json approved-job.json
```

The worker prompts locally, writes `jobId.teclicense` and reports its licence ID.
It must not be connected directly to unauthenticated upload folders or email.

## Required commissioning and remaining automation

1. Review code and approval authority design; implement the authenticated adapter
   to existing independent approvals, rejecting stale/revoked jobs and recording
   the reviewer/MFA audit linkage. A signed file alone is not a new human approval.
2. Verify Windows ACLs, dedicated account, encrypted device/backup, queue/file
   ownership and anti-malware exclusions only if explicitly justified.
3. On synthetic keys test issuance, modified claims, wrong pin, replay, duplicate
   approval, expiry, crash/restart and failed delivery/retry. Tests in
   `tests/assurance/licence-worker.test.cjs` cover the core local boundary.
4. Witness the production public-key match and one controlled customer install;
   preserve evidence and retain the original encrypted private key offline.
5. Implement delivery acknowledgements, operator alerts, approval revocation checks,
   rotation and encrypted ledger/key recovery. Do not enable unattended key unlock
   or customer delivery until those boundaries are commissioned.

The ledger contains licence claims and must be backed up privately. SQLite durability
is not a tamper-proof external audit service. A compromised operator holding both
private keys can bypass separation; protect the approval authority separately.
