# TEC EPR 1.0.0 staging read-back and revocation evidence

**Scope:** TCL customer gateway only, PR #38. Do not edit, rebuild, replace, or republish the signed Clinic Edition master archive, detached signatures, publisher private key, or any clinical database. All tests must use the dedicated staging gateway database. The release remains pinned by `download_policy.py`.

## Gate A — Verify the actual downloaded bytes (pending live operator evidence)

The previous successful R2 HEAD only proved the stored object's recorded byte count and ETag. It did **not** establish SHA-256 integrity or publisher authenticity.

1. On a trusted customer test workstation, retain the archive obtained via the gateway's short-lived, authenticated, authorized link. Do not paste signed URLs, cookies, R2 credentials or WorkOS challenges into a terminal transcript or chat.
2. From the repository root, run with the path to the **already downloaded** archive:
   ```powershell
   python customer_gateway/verify_downloaded_release.py --file "C:\\PrivateTest\\TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz" --evidence-json "C:\\PrivateTest\\readback-evidence.json"
   ```
   The verifier uses streamed reads, compares 329965422 bytes and SHA-256
   `e1c75bb867627cb60f0f5ff9737b602661550a15df75f5df52bf8c43835c8c0e`,
   and returns exit code 0 only when **both** match. Exit 1 indicates a mismatch
   (block installation); exit 2 indicates input/evidence file error. An existing
   evidence file will not be overwritten. The command performs no network requests.
3. Independently verify the release's **detached RSA-4096 signature** using the publisher's independently authenticated *public* key and the matching signed manifest/release instruction. Confirm the expected publisher public-key SPKI SHA-256 fingerprint:
   `6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733`.
   Do not improvise a signature-verification command without knowing the exact
   signed payload, signature encoding, padding and digest. Do not distribute the
   private signing key. Hash-only PASS is **not** a signature PASS.
4. Retain the actual return code, SHA-256, size, signing verification evidence,
   timestamp, staging release ID and two-party review; exclude URL query strings,
   identifiers of patients, credentials, or sensitive customer data.

## Gate B — Revocation and isolation (pending live acceptance)

Use synthetic staging tenant / controlled WorkOS test identities. Keep production
flags off. In an **expressly authorized staging release test** only, an owner-authorized
proposer requests access, a distinct appointed administrator with current MFA approves,
and a controlled customer with active membership signs in.

1. Before approval: assert that issuing any download URL is denied.
2. After approval and only while both explicit staging flags are enabled: issue a
   test URL and record the timestamp and a **redacted** audit event. Download and
   verify the bytes using Gate A; do not record the URL itself.
3. Revoke the grant through the authenticated administrator dashboard, then request
   a **new** URL with the original customer. Expect 403, no new issuance audit and
   no new URL. Confirm another customer's tenant access is denied.
4. An **already issued** R2 presigned URL remains valid until its own expiration;
   gateway grant revocation does not invalidate it. Verify that it no longer works
   **after expiration**, allowing for service clock skew. If immediate revocation of
   already issued links is a hard requirement, do not launch with direct presigned R2
   GET URLs; use a streaming delivery proxy that re-authorizes each transfer, or
   another design allowing active token invalidation.
5. Disable both flags again immediately after staging acceptance and preserve
   auditable results. Test app session expiry and disabled administrator access.
   Confirm the gateway remains isolated from CRM and clinical databases.

## Gate C — Formal production controls (not approved)

- Independent review of the gateway PR and pinned release provenance; review
  provider-session revocation propagation, authenticator recovery, concurrent
  approve/revoke races, ingress/proxy log redaction, retention and protected audit
  export, bucket-read-only credential scope, and bucket public access restrictions.
- End-to-end delivery, expiry, negative authorization and integrity evidence from
  real staging; do not treat mocked unit tests as proof of R2 retrieval.
- Final contract, pricing, support, licensing, security and privacy decisions.
- An independent production deployment design and formal owner sign-off. The
  present `from_environment()` guard intentionally **refuses non-staging** and
  must not be bypassed as part of this verification exercise.

**Current status:** implementation of the offline read-back verifier and synthetic
revocation regression is available on draft PR #38. Neither a full live file
read-back nor live revocation acceptance is attested by the source changes alone.

## Gate A2 — Verify publisher-signed manifest (read-only)

The operator has identified `manifest.json`, `manifest.sig` (685 encoded bytes)
and `manifest.signer.json` for the untouched 1.0.0 signed release. Reported
signer metadata: `kind=TEC EPR clinical distribution release manifest`,
`algorithm=RSA-SHA256`, `releaseVersion=1.0.0`, and the previously recorded
publisher SPKI SHA-256
`6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733`.
The operator found a `public.pem` **inside an encrypted off-host restore
folder**. That is **not automatically the release signing public key**; it
may belong to a different backup/restore identity. Do not trust it on name alone.

A new offline script `customer_gateway/verify_release_manifest.py` checks:

1. Trusted, code-pinned publisher SPKI SHA-256 matches signer metadata.
2. The candidate key imports as a public key and its DER SubjectPublicKeyInfo
   SHA-256 matches the trusted pinned fingerprint. Mismatch **fails closed**.
3. Base64-encoded RSA-4096 detached signature is exactly 512 decoded bytes.
4. OpenSSL verifies RSA-SHA256 PKCS#1 v1.5 over **the exact bytes** of a
   temporary, read-only snapshot of `manifest.json`.

Run locally **only after checking the public-key provenance** (no private key
input is needed):

```powershell
cd C:\My_Applications\TCL-gateway-verification
git pull --ff-only origin feature/gateway-entitlement-approvals
python .\customer_gateway\verify_release_manifest.py `
  --release-dir "C:\My_Applications\TEC-EPR-Commercial-Releases\TEC-EPR-Clinic-Edition-1.0.0-SIGNED-1d7024f7955a" `
  --public-key "C:\My_Applications\TEC-EPR-Release-Assurance-1.0.0\encrypted-offhost-restore\public.pem"
```

If that is a backup/restore key, a `PUBLIC KEY MISMATCH` result is expected,
**not a signature verification PASS**. Find the authentic **release publisher
public key** through the protected signing procedure, and rerun using its path.
Do not move, upload or disclose the publisher private key.

The script does not modify the signed master, manifest or clinical databases;
synthetic tamper/mismatched-key tests are in `test_verify_release_manifest.py`.
Even a successful manifest signature check does **not** automatically establish
that the signed manifest semantically binds to the R2 archive. Inspect the
manifest's release object/path/hash/byte-count claims and cross-check the
already verified downloaded 329,965,422-byte archive separately. No production
sign-off can be inferred from this individual signature check.
