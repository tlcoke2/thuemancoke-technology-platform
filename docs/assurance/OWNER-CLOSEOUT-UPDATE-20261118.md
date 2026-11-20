# Owner closeout update — 18 November 2026

This updates the register using the owner's explicit report in this conversation.
It does not request repeated permission or substitute for the underlying records.

- Clinical, legal and privacy work: **owner reports completed in-house**. Preserve
  that status and link the existing internal decisions when the private evidence
  set is assembled. Do not label it an independent penetration assessment,
  worldwide medical-device clearance or an externally issued certification.
- Cloudflare: the owner confirms authentication and protected access were
  completed through Microsoft Edge on the owner's laptop with assisted work and
  verification. The cloud browser is not the working authentication route. Use
  owner-assisted Edge readback if any specific configuration evidence is needed;
  do not repeatedly ask the owner to log into the cloud browser. Existing account
  authentication alone does not document every WAF rule, exception or test alert.
- Both price structures are intentional: Jamaica/JMD and regional USD. New source
  binds the installed region to a persistent pricing profile and consistent labels.
  Independent catalogue amounts are retained; no automatic conversion is applied.
- A protected desktop issuer package is prepared with the existing GUI, pinned
  public-key/encrypted-key preflight, Windows ACL inspection and durable duplicate
  prevention. The owner must launch it locally and enter the passphrase there.
  This workspace cannot operate the owner's Windows computer or unlock its key.

## Engineering references

Backend candidate: https://github.com/tlcoke2/tec_epr_backend/pull/84
Frontend candidate: https://github.com/tlcoke2/tec_epr_frontend/pull/6

Nineteen focused backend/desktop tests pass locally. Regional frontend review
check passes with aliases configured and existing unused-symbol checks disabled.
Windows syntax is checked separately in CI. The source change is a new candidate,
not an alteration of the immutable signed release or an in-place customer upgrade.
Complete image rebuild/scans, migration acceptance where applicable and installed
regional UAT remain required for publication of changed clinical binaries.

Package: TEC-EPR-Protected-Licence-Issuer.zip
SHA-256: 59681d8ac57f63b34db529893fc8c0f784c4ca51575334f2b22e5ee13d054cd8
The package contains no private key. Extraction does not commission unattended
signing; local preflight, actual key unlock and customer import must be evidenced.

## Hosted verification blocker

GitHub Actions run 44451148797 did not execute either the Linux test job or
Windows parser job. The authenticated GitHub run summary states: "The job was
not started because recent account payments have failed or your spending limit
needs to be increased." This is an account billing/spending-limit blocker, not a
passing check or a demonstrated test failure. Other new private-repository runs
also stopped before steps. No billing setting was changed. Candidate PRs remain
open; publication/merging of clinical changes is not represented as complete.

Owner action: resolve GitHub Actions billing/spending availability, then rerun
the existing candidate jobs. Do not re-sign or overwrite the current release.
The Windows desktop source package is available for local preflight; a real Windows
parse/launch and production-key unlock are still to be confirmed on the owner PC.
