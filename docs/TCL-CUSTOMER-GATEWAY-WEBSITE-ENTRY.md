# TCL website → secure customer gateway entry (planned commercial release)

## Requirement and release position

The owner requires the completed TCL customer gateway, including customer entitlement and download pages, to be reachable through the main TCL website at **`https://www.thuemancokelimited.com`** (and the canonical apex). The approved design is a **public entry page** linking into the **separately hosted, authenticated gateway**, not a public reproduction of a user's customer/administrator account page.

PR branch `feature/customer-gateway-website-entry` is intentionally independent of the gateway's still-draft PR #38. **Do not deploy/merge until site review and production cutover approval**. Customer account details and synthetic staging grants are not bundled into the static website.

The public marketing site will provide:

- Home navigation → `./customer-portal.html`.
- Enterprise software page navigation and hero CTA → `./customer-portal.html`.
- Branded `customer-portal.html` public gateway entry; public until the authorised gateway link is enabled.
- When enabled, a link to **`/auth/login`** on a separately approved HTTPS TCL production gateway origin, where the WorkOS sign-in and authorisation rules continue to apply.
- No public access to `/admin/customers`, grant IDs, customer subjects, email addresses, contract/approval references, clinical databases, or raw software download URLs.

## Fail-closed activation

GitHub Pages production builds use Vite's `software-config.js` generated asset. New build variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_CUSTOMER_GATEWAY_PUBLIC_ENABLED` | `false` | When `true`, show the authenticated gateway login CTA. |
| `VITE_CUSTOMER_GATEWAY_ORIGIN` | absent | HTTPS **origin only**, not a path. Recommended: `https://customers.thuemancokelimited.com` once fully configured. |

The **disabled/default** page displays production access pending review and offers the existing software enquiry form instead. The website does not disclose the isolated Railway staging gateway URL. A production build fails if the portal link is enabled without an origin, or if the origin is not an approved `*.thuemancokelimited.com` hostname; staging hosts, basic-auth URL credentials, ports, paths and queries are rejected. The gateway itself also independently enforces access; link visibility is not an authorisation boundary.

**Commercial activation checklist:** 

1. Complete live customer-grant revocation, cross-tenant isolation and already-issued R2 presigned-GET expiry tests from PR #38.
2. Complete independent review of WorkOS provider-session revocation, MFA recovery, gateway audit retention, R2 credential scope and private-bucket access, protection against abuse and support policies.
3. Deploy a separately approved **production gateway instance** with dedicated commercial database and reviewed environment settings. The current gateway code's `APP_ENV=staging` safeguard must not be removed as a shortcut to activation.
4. Establish and verify a dedicated custom domain such as `customers.thuemancokelimited.com` through Railway and Cloudflare HTTPS, configure exact WorkOS callback/auth/logout URLs, and verify cookie/CSRF behaviour across both sites. No browser-side secrets, local-storage tokens or public R2 links.
5. Confirm authorisation to market/distribute TEC EPR, commercial agreement, privacy notice and licensing handoff; separately verify end-to-end customer onboarding and licence controls.
6. After signed owner go/no-go, merge this *separate* website PR to `main`, deploy GitHub Pages, and deliberately configure `VITE_CUSTOMER_GATEWAY_PUBLIC_ENABLED=true` and `VITE_CUSTOMER_GATEWAY_ORIGIN=https://<approved-host>` in the Pages build environment; redeploy. Do not enable either flag before the go/no-go. Validate links from `www` and apex, browser accessibility, mobile UX and no leaked staging addresses.

## Staging test evidence and privacy

The owner reported one synthetic gateway entitlement **revoked** and another **approved**, both used for controlled staging customer validation. This indicates the displayed grant states, but the excerpt alone does **not** prove a denied new URL after revocation, two-person independent approval, cross-customer isolation, or expiry of an already minted URL. These are separate acceptance requirements.

Do not add the synthetic test subject identifier, email address, grant IDs, contract/approval references, sign-in cookies or any customer-specific data to the public static site or repository documentation. When the release is accepted, the marketing page points to the gateway's **login**, not the admin review URL, and the gateway determines which account/entitlements to show after authentication.

## Safe rollback

Disable `VITE_CUSTOMER_GATEWAY_PUBLIC_ENABLED` and rebuild/redeploy the static Pages website to hide the login CTA without altering gateway grants or user accounts. If customer identity or entitlement logic fails, disable production downloads **server-side** as a separate incident response. This website switch never substitutes for gateway-side revocation.
