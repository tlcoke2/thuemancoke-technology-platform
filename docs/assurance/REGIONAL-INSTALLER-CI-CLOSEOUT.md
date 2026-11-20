# Regional installer engineering closeout

Backend reviewed commit: `01973ff22846c4a41a5a7072bcc1e3613701679f`.
Frontend reviewed commit: `3eef2305a66acd5da30c6a2f596bf8f03f006e17`.

All 23 backend workflow runs passed. Private frontend read access is resolved.

| Acceptance | Workflow run | Result |
| --- | --- | --- |
| Actual customer-package bootstrap, signed licence HTTP, restart, database/uploads restore and independently parsed laboratory PDF | 44459083872 | Passed |
| Real three-container integration | 44459083732 | Passed |
| Bounded clinical isolation and database outage/restart recovery | 44459083726 | Passed |
| Local offline archive save/load, old/new image retention and fresh-schema replay | 44459083800 | Passed |

Actual packaged backend/frontend/PostgreSQL reports each contain zero Critical/High
findings at scan time. The PostgreSQL builder uses pinned Go 1.27.4; public/runtime
package files remain readable under a restrictive publisher umask, while secrets
retain restrictive permissions. Private evidence ZIPs and digests are preserved at
backend evidence commit `5076a1600d8e826d759c01d799cf56774a853bdc`.

Source merges: backend `f62e7d1879e3c5c71844cc9bab071767a376c804`, frontend
`70c221b8e1d8e42952c5227deb823d64d54ca268`.
Jamaica/JMD, US/USD and UK-Europe/USD remain independent regional price lists,
without automatic currency conversion. The owner reports successful protected
Windows desktop licence issuance.

The passive live gateway check passed 12 fixed checks; its full report is adjacent.
It does not assess authenticated workflows, WAF account settings or penetration resistance.

These synthetic Linux CI tests do not replace independent Windows clean-computer
acceptance of newly assembled bytes. A separate regional distribution must be
assembled, scanned, accepted, locally publisher-signed and read back from private
R2 before updating the portal release pin. No new signed commercial archive is
claimed here. Existing archive, private keys, licences and production volumes are preserved.
