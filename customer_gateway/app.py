import base64
import hashlib
import html
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, delete, insert, select


metadata = MetaData()
flows = Table("gateway_auth_flows", metadata,
    Column("state_hash", String(64), primary_key=True),
    Column("browser_hash", String(64), nullable=False),
    Column("verifier", String(128), nullable=False),
    Column("expires", Integer, nullable=False))
sessions = Table("gateway_sessions", metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("subject", String(160), nullable=False),
    Column("csrf", String(80), nullable=False),
    Column("expires", Integer, nullable=False))
audit = Table("gateway_auth_audit", metadata,
    Column("id", String(64), primary_key=True),
    Column("event", String(40), nullable=False),
    Column("subject", String(160), nullable=False),
    Column("created", Integer, nullable=False))

FLOW_COOKIE = "__Host-tcl-flow"
SESSION_COOKIE = "__Host-tcl-session"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    origin: str
    client_id: str
    api_key: str
    enabled: bool = False
    mfa_enabled: bool = False
    enrollment_subjects: tuple[str, ...] = ()
    onboarding_enabled: bool = False
    downloads_enabled: bool = False
    release_approved: bool = False

    def __post_init__(self):
        u = urlsplit(self.origin)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.path or u.query or u.fragment:
            raise ValueError("GATEWAY_ORIGIN must be an HTTPS origin with no trailing slash")
        if not self.client_id.startswith("client_") or not self.api_key.startswith("sk_"):
            raise ValueError("Staging WorkOS configuration missing")


class WorkOS:
    def __init__(self, config):
        self.config = config

    def exchange(self, code, verifier):
        # HTTPS server-to-server exchange. No browser-provided JWT or user object is trusted.
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.post("https://api.workos.com/user_management/authenticate", json={
                "client_id": self.config.client_id, "client_secret": self.config.api_key,
                "grant_type": "authorization_code", "code": code, "code_verifier": verifier})
            response.raise_for_status()
            return response.json()


def create_app(config, engine, provider=None, clock=time.time, mfa_provider=None, identity_lookup=None, download_signer=None):
    provider = provider or WorkOS(config)
    try:
        from .ui import page as view, message_page, STYLESHEET
    except ImportError:
        from ui import page as view, message_page, STYLESHEET
    try:
        from .mfa import StepUp, WorkOSMFA, MFAError, elevations, metadata as access_metadata
    except ImportError:
        from mfa import StepUp, WorkOSMFA, MFAError, elevations, metadata as access_metadata
    try:
        from .entitlements import Entitlements, Denied, admins, grants
    except ImportError:
        from entitlements import Entitlements, Denied, admins, grants
    entitlements = Entitlements(engine, sessions, clock)
    try:
        from .downloads import Downloads, Denied as DownloadDenied
    except ImportError:
        from downloads import Downloads, Denied as DownloadDenied
    download_service = Downloads(entitlements, download_signer, config.downloads_enabled, config.release_approved)
    step_up = StepUp(engine, sessions, audit, mfa_provider or WorkOSMFA(config.api_key), clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/assets/gateway.css", include_in_schema=False)
    def gateway_css():
        return Response(STYLESHEET, media_type="text/css; charset=utf-8")

    @app.exception_handler(StarletteHTTPException)
    async def browser_error(request: Request, error: StarletteHTTPException):
        # Health probes remain machine-readable; form/page errors must never
        # expose unstyled FastAPI JSON ("detail") in the customer browser.
        if request.url.path in ("/health", "/ready"):
            return JSONResponse({"detail": "Gateway health check failed"}, status_code=error.status_code)
        detail = error.detail if isinstance(error.detail, str) else "The operation could not be completed."
        title = {
            400: "Unable to complete request", 401: "Please sign in again",
            403: "Access not permitted", 404: "Page not found",
            405: "Action not available", 413: "Form too large",
            415: "Unsupported form", 503: "Service temporarily unavailable",
        }.get(error.status_code, "Request not completed")
        if error.status_code == 401:
            detail = "Your gateway session has expired, or you need to sign in again."
        elif error.status_code == 404:
            detail = "That page is not available. Return to the gateway to continue."
        response = HTMLResponse(message_page(title, detail,
            action="/auth/login" if error.status_code == 401 else "/",
            action_label="Sign in securely" if error.status_code == 401 else "Return to gateway"),
            status_code=error.status_code)
        if error.headers:
            response.headers.update(error.headers)
        return response

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        # Fail closed, do not display internal exception text or provider secrets.
        if request.url.path in ("/health", "/ready"):
            return JSONResponse({"detail": "Gateway check unavailable"}, status_code=500)
        return HTMLResponse(message_page("Something went wrong",
            "The action could not be confirmed. Please return to your account "
            "and try again, or contact your administrator.",
            action="/account", action_label="Return to account",
            eyebrow="SECURE RECOVERY"), status_code=500)


    @app.middleware("http")
    async def security(request, call_next):
        # No dependence on attacker-controlled forwarded host for redirects or cookies.
        if request.url.hostname != urlsplit(config.origin).hostname and request.url.path != "/health":
            return HTMLResponse("Invalid host", status_code=400)
        response = await call_next(request)
        # HTML form POSTs under no-referrer can send Origin: null. Only the
        # account page needs same-origin; keep callback codes fully suppressed.
        policy = "same-origin" if request.url.path in ("/account", "/auth/mfa", "/auth/mfa/enroll", "/admin", "/admin/customers", "/customer") else "no-referrer"
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": policy,
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            "Strict-Transport-Security": "max-age=31536000"})
        if request.url.path == "/auth/mfa/enroll":
            response.headers["Content-Security-Policy"] += "; img-src data:"
        return response

    def enabled():
        if not config.enabled:
            raise HTTPException(503, "Staging sign-in is disabled")

    def cookie(response, name, value, ttl):
        response.set_cookie(name, value, max_age=ttl, secure=True, httponly=True,
                            samesite="lax", path="/")

    def current(request):
        enabled()
        token = request.cookies.get(SESSION_COOKIE, "")
        if not token or len(token) > 128:
            raise HTTPException(401, "Sign in required")
        with engine.connect() as c:
            row = c.execute(select(sessions).where(sessions.c.token_hash == digest(token),
                            sessions.c.expires > int(clock()))).mappings().first()
        if not row:
            raise HTTPException(401, "Session expired or revoked")
        return row

    @app.get("/health")
    def health():
        return {"ok": True, "environment": "staging", "service": "tcl-customer-gateway",
                "downloadsEnabled": config.downloads_enabled and config.release_approved and download_signer is not None, "mfaStepUpEnabled": config.mfa_enabled,
                "authenticatorSetupAvailable": bool(config.enrollment_subjects),
                "customerOnboardingEnabled": config.onboarding_enabled}

    @app.get("/ready")
    def ready():
        with engine.connect() as c:
            c.execute(select(sessions.c.token_hash).limit(1))
            if config.mfa_enabled:
                for table in access_metadata.sorted_tables:
                    c.execute(select(table).limit(0))
            if config.onboarding_enabled:
                c.execute(select(customer_requests).limit(0))
        return {"ready": True}

    @app.get("/", response_class=HTMLResponse)
    def home():
        sign_in = ('<a class="button" href="/auth/login">Sign in securely</a>' if config.enabled
                   else '<p class="notice warn">Sign-in is currently disabled.</p>')
        release_status = ('Controlled staging downloads are enabled'
                          if config.downloads_enabled and config.release_approved
                          else 'Private downloads require active, approved access')
        return view("Secure software. Clear customer access.",
            '<div class="grid"><section class="card panel-gradient">'
            '<span class="kicker">TCL SOFTWARE DELIVERY</span>'
            '<h2>TEC EPR Clinic Edition 1.0.0</h2>'
            '<p>Secure access to your software entitlement, private release download '
            'and verification information.</p><div class="actions">' + sign_in
            + '</div><p class="fine">Access is subject to identity verification and authorisation.</p>'
            '</section><section class="card"><h2>What you can expect</h2>'
            '<ul class="feature-list">'
            '<li>Verified sign-in and protected account sessions</li>'
            '<li>Independent administrator approval of customer access</li>'
            '<li>Time-limited private downloads with access controls</li>'
            '<li>Documented file-integrity and publisher verification</li></ul>'
            '<div class="notice">' + html.escape(release_status) + '</div></section></div>'
            '<section class="card"><div class="segment"><div><span class="kicker">'
            'ACCOUNT SUPPORT</span><h2>Already registered?</h2>'
            '<p class="muted">Check your customer status or contact TCL if your '
            'organisation is awaiting approval.</p></div>'
            '<a class="button secondary" href="/account">My account</a></div></section>',
            eyebrow="PROTECTED CUSTOMER EXPERIENCE",
            intro="Your trusted portal for software access, verification and secure delivery.")

    @app.get("/signed-out", response_class=HTMLResponse)
    def signed_out():
        return view("You have signed out",
            '<section class="card"><span class="stat">Gateway session ended</span>'
            '<h2>Your TCL gateway session has been closed.</h2>'
            '<p>This signs you out of the gateway only. Your identity-provider '
            'single sign-on session may remain active.</p>'
            '<div class="actions"><a class="button" href="/auth/login">Sign in again</a>'
            '<a class="button secondary" href="/">Return to gateway</a></div>'
            '<p class="fine">On shared computers, also sign out of your identity '
            'provider and close your browser.</p></section>',
            eyebrow="SESSION COMPLETE")

    @app.get("/auth/login")
    def login(request: Request):
        enabled()
        now = int(clock())
        state, browser, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        with engine.begin() as c:
            c.execute(delete(flows).where(flows.c.expires <= now))
            c.execute(delete(sessions).where(sessions.c.expires <= now))
            # Invalidate an earlier login flow from the same browser.
            old = request.cookies.get(FLOW_COOKIE, "")
            if old:
                c.execute(delete(flows).where(flows.c.browser_hash == digest(old)))
            c.execute(insert(flows).values(state_hash=digest(state), browser_hash=digest(browser),
                        verifier=verifier, expires=now+600))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        params = dict(client_id=config.client_id, provider="authkit", response_type="code",
                      redirect_uri=config.origin+"/auth/callback", state=state,
                      code_challenge=challenge, code_challenge_method="S256")
        response = RedirectResponse("https://api.workos.com/user_management/authorize?"+urlencode(params), 303)
        cookie(response, FLOW_COOKIE, browser, 600)
        return response

    @app.get("/auth/callback")
    def callback(request: Request):
        enabled()
        state, code = request.query_params.get("state", ""), request.query_params.get("code", "")
        browser = request.cookies.get(FLOW_COOKIE, "")
        if not state or not browser or len(state) > 128 or len(browser) > 128 or not code or len(code) > 4096:
            raise HTTPException(400, "Invalid sign-in callback")
        with engine.begin() as c:
            # Atomic single-use consumption, including across multiple service replicas.
            flow = c.execute(delete(flows).where(flows.c.state_hash == digest(state),
                flows.c.browser_hash == digest(browser), flows.c.expires > int(clock()))
                .returning(flows.c.verifier)).first()
        if not flow:
            raise HTTPException(400, "Expired, replayed or mismatched sign-in")
        try:
            data = provider.exchange(code, flow.verifier)
            user = data.get("user", {})
            subject = user.get("id")
            if data.get("impersonator") or data.get("authentication_method") == "Impersonation":
                raise ValueError("Impersonated identities are not supported")
            if user.get("email_verified") is not True or not isinstance(subject, str) or not subject.startswith("user_") or len(subject) > 160:
                raise ValueError("Unverified identity")
        except Exception:
            # Never log provider responses, authorization codes or tokens.
            raise HTTPException(401, "Sign-in could not be verified; please start again") from None
        token, csrf, now = secrets.token_urlsafe(32), secrets.token_urlsafe(32), int(clock())
        with engine.begin() as c:
            old = request.cookies.get(SESSION_COOKIE, "")
            if old:
                c.execute(delete(sessions).where(sessions.c.token_hash == digest(old)))
            c.execute(insert(sessions).values(token_hash=digest(token), subject=subject, csrf=csrf, expires=now+900))
            c.execute(insert(audit).values(id=secrets.token_hex(16), event="staging_login", subject=subject, created=now))
        response = RedirectResponse("/account", 303)
        cookie(response, SESSION_COOKIE, token, 900)
        response.delete_cookie(FLOW_COOKIE, secure=True, httponly=True, samesite="lax", path="/")
        return response

    @app.get("/account", response_class=HTMLResponse)
    def account(request: Request):
        row = current(request)
        mfa_html = ""
        is_admin = False
        if config.mfa_enabled:
            with engine.connect() as c:
                elevation = c.execute(select(elevations.c.expires).where(
                    elevations.c.session_hash == row['token_hash'],
                    elevations.c.subject == row['subject'],
                    elevations.c.expires > int(clock()))).first()
                is_admin = c.execute(select(admins.c.subject).where(
                    admins.c.subject == row["subject"], admins.c.active.is_(True))).first() is not None
            mfa_html = ("<p>Additional verification: " + ("verified for this session" if elevation else "required")
                + "</p><p>Account ID: <code>" + html.escape(row['subject']) + "</code></p>"
                + "<form action='/auth/mfa/start' method='post'><input type='hidden' name='csrf' value='"
                + row['csrf'] + "'><button>Verify authenticator</button></form>")
            if row['subject'] in config.enrollment_subjects and not elevation:
                mfa_html += ("<p>If you have never enrolled an authenticator for this account:</p>"
                    "<form action='/auth/mfa/enroll' method='post'><input type='hidden' name='csrf' value='"
                    + row['csrf'] + "'><button>Set up authenticator</button></form>")
        role_html = (
            '<span class="stat">Gateway administrator / approver</span>'
            '<h2>Administrator access</h2><p>Your email has been verified, and '
            'your administrator appointment is active.</p>'
            '<p>Recent authenticator verification is required for privileged actions.</p>'
            '<div class="actions"><a class="button" href="/admin">Approval dashboard</a></div>'
            '<p class="fine">An administrator appointment does not automatically '
            'grant a software licence or customer download.</p>'
        ) if is_admin else (
            '<span class="stat pending">Customer account</span>'
            '<h2>My access</h2><p>Your email has been verified. '
            'Customer entitlements still require independent approval.</p>'
            '<p class="fine">Signing in never creates download permissions or a licence.</p>'
        )
        if config.onboarding_enabled:
            role_html += '<div class="actions"><a class="button secondary" href="/customer">View customer access</a></div>'
        body = (
            '<div class="grid"><section class="card">' + role_html + '</section>'
            '<section class="card"><span class="kicker">ACCOUNT SECURITY</span>'
            '<h2>Additional verification</h2>' + mfa_html + '</section></div>'
            '<section class="card"><div class="segment"><div><h2>Manage session</h2>'
            '<p class="muted">Signing out ends this gateway session; '
            'it does not end your identity-provider single sign-on session.</p></div>'
            '<form action="/auth/logout" method="post">'
            '<input type="hidden" name="csrf" value="' + html.escape(row["csrf"], quote=True) + '">'
            '<button class="secondary">Sign out securely</button></form></div></section>'
        )
        return view("Welcome to your account", body,
            eyebrow="AUTHENTICATED CUSTOMER PORTAL",
            intro="Manage identity verification, check approved access and continue to secure downloads.")

    async def protected_form(request, row):
        if request.headers.get("origin") != config.origin:
            raise HTTPException(403, "Origin rejected")
        if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
            raise HTTPException(415, "Form required")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > (2048 if request.url.path == "/admin/customers/propose" else 512):
                raise HTTPException(413, "Form too large")
        from urllib.parse import parse_qs
        fields = parse_qs(body.decode("utf-8", errors="replace"))
        if any(len(values) != 1 for values in fields.values()):
            raise HTTPException(400, "Duplicate form fields")
        if not secrets.compare_digest(fields.get("csrf", [""])[0], row["csrf"]):
            raise HTTPException(403, "CSRF check failed")
        return fields

    def mfa_ready():
        if not config.mfa_enabled:
            raise HTTPException(503, "Additional verification is disabled")

    @app.post("/auth/mfa/enroll", response_class=HTMLResponse)
    async def mfa_enroll(request: Request):
        row = current(request)
        mfa_ready()
        await protected_form(request, row)
        try:
            key, qr = step_up.enroll(row["token_hash"], config.enrollment_subjects)
        except MFAError as error:
            return HTMLResponse("<h1>Authenticator setup</h1><p>" + html.escape(str(error))
                + "</p><a href='/account'>Return to account</a>", status_code=400)
        qr_html = ("<img width='256' height='256' alt='Authenticator setup QR code' src='"
                   + html.escape(qr, quote=True) + "'>") if qr else ""
        return ("<h1>Set up your authenticator</h1><p>Add an account in your authenticator app. "
            "Scan this QR code, or enter the setup key manually as a time-based account.</p>"
            + qr_html + "<p>Account: TCL Customer Gateway</p><p>Setup key: <code>"
            + html.escape(key) + "</code></p><p>Keep this page private. Add the account before "
            "leaving this page; the setup key will not be shown again.</p>"
            "<p>Enter the six-digit code from your app to confirm setup.</p>"
            "<form action='/auth/mfa/verify' method='post'><input type='hidden' name='csrf' value='"
            + row['csrf'] + "'><label>Authenticator code <input name='code' inputmode='numeric' "
            "autocomplete='one-time-code' pattern='[0-9]{6}' maxlength='6' required></label>"
            "<button>Confirm authenticator</button></form>")

    @app.post("/auth/mfa/start")
    async def mfa_start(request: Request):
        row = current(request)
        mfa_ready()
        await protected_form(request, row)
        try:
            step_up.begin(row["token_hash"])
        except MFAError as error:
            raise HTTPException(400, str(error)) from None
        return RedirectResponse("/auth/mfa", 303)

    @app.get("/auth/mfa", response_class=HTMLResponse)
    def mfa_page(request: Request):
        row = current(request)
        mfa_ready()
        return ("<h1>Verify your authenticator</h1><p>Enter the current six-digit code. "
                "This verifies your session; it does not grant administrator or download access.</p>"
                "<form action='/auth/mfa/verify' method='post'><input type='hidden' name='csrf' value='"
                + row['csrf'] + "'><label>Authenticator code <input name='code' inputmode='numeric' "
                "autocomplete='one-time-code' pattern='[0-9]{6}' maxlength='6' required></label>"
                "<button>Verify</button></form><a href='/account'>Return to account</a>")

    @app.post("/auth/mfa/verify")
    async def mfa_verify(request: Request):
        row = current(request)
        mfa_ready()
        fields = await protected_form(request, row)
        try:
            step_up.verify(row["token_hash"], fields.get("code", [""])[0])
        except MFAError as error:
            raise HTTPException(400, str(error)) from None
        return RedirectResponse("/account", 303)

    @app.get("/admin", response_class=HTMLResponse)
    def admin_page(request: Request):
        row = current(request)
        mfa_ready()
        try:
            with engine.begin() as c:
                entitlements._actor(c, row['token_hash'], int(clock()))
                records = c.execute(select(grants).order_by(grants.c.id).limit(100)).mappings().all()
        except Denied:
            return HTMLResponse("<h1>Approval dashboard</h1><p>An appointed administrator and recent "
                "authenticator verification are required.</p><a href='/account'>Return to account</a>", status_code=403)
        content = "<h1>Approval dashboard — Staging</h1><p>A download grant does not issue a software licence.</p>"
        if config.onboarding_enabled:
            content += "<p><a href='/admin/customers'>Customer onboarding and review</a></p>"
        if not records:
            content += "<p>No download grant requests are awaiting review.</p>"
        else:
            content += "<p>Showing up to 100 grants.</p><table><tr><th>Grant</th><th>Tenant</th>"
            content += "<th>State</th><th>Release</th><th>Proposed by</th><th>Starts (UTC)</th><th>Expires (UTC)</th><th>Contract reference</th><th>Approval reference</th><th>Action</th></tr>"
            for g in records:
                esc = lambda v: html.escape(str(v), quote=True)
                actions = ""
                if g['state'] == 'pending' and g['proposer'] != row['subject']:
                    actions += ("<form method='post' action='/admin/grants/" + esc(g['id'])
                        + "/approve'><input type='hidden' name='csrf' value='" + row['csrf']
                        + "'><button>Approve</button></form>")
                if g['state'] != 'revoked':
                    actions += ("<form method='post' action='/admin/grants/" + esc(g['id'])
                        + "/revoke'><input type='hidden' name='csrf' value='" + row['csrf']
                        + "'><button>Revoke</button></form>")
                content += "<tr>" + "".join("<td>" + esc(datetime.fromtimestamp(g[k], timezone.utc).strftime("%d %b %Y %H:%M") if k in ("starts", "expires") else g[k]) + "</td>" for k in
                    ('id','tenant_id','state','release_id','proposer','starts','expires','contract_reference','approval_reference')) + "<td>" + actions + "</td></tr>"
            content += "</table>"
        return content + "<p><a href='/account'>Return to account</a></p>"

    @app.post("/admin/grants/{grant_id}/{action}")
    async def admin_action(grant_id: str, action: str, request: Request):
        row = current(request)
        mfa_ready()
        await protected_form(request, row)
        if len(grant_id) > 64 or action not in ('approve', 'revoke'):
            raise HTTPException(400, "Invalid action")
        try:
            operation = entitlements.approve if action == 'approve' else entitlements.revoke
            if config.onboarding_enabled and action == 'approve':
                with engine.connect() as c:
                    onboard = c.execute(select(customer_requests.c.id).where(customer_requests.c.id == grant_id)).first()
                if onboard:
                    operation = onboarding_service.approve
            operation(row['token_hash'], grant_id)
        except Denied as error:
            raise HTTPException(403, str(error)) from None
        return RedirectResponse('/admin', 303)

    @app.post("/auth/logout")
    async def logout(request: Request):
        row = current(request)
        if request.headers.get("origin") != config.origin:
            raise HTTPException(403, "Origin rejected")
        body = await request.body()
        if len(body) > 256:
            raise HTTPException(400, "Invalid request")
        from urllib.parse import parse_qs
        csrf = parse_qs(body.decode("utf-8", errors="replace")).get("csrf", [""])[0]
        if not secrets.compare_digest(csrf, row["csrf"]):
            raise HTTPException(403, "CSRF check failed")
        with engine.begin() as c:
            c.execute(delete(sessions).where(sessions.c.token_hash == row["token_hash"]))
            c.execute(insert(audit).values(id=secrets.token_hex(16), event="staging_logout",
                                          subject=row["subject"], created=int(clock())))
        response = RedirectResponse("/signed-out", 303)
        response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")
        return response

    @app.post("/api/downloads", response_class=HTMLResponse)
    async def downloads(request: Request):
        row = current(request)
        if not config.downloads_enabled or not config.release_approved:
            raise HTTPException(403, "Downloads are not enabled")
        fields = await protected_form(request, row)
        grant_id = fields.get('grant_id', [''])[0]
        if not grant_id or len(grant_id) > 64:
            raise HTTPException(400, "Invalid download request")
        try:
            url, decision = download_service.issue(row['token_hash'], grant_id)
        except DownloadDenied as error:
            raise HTTPException(403, str(error)) from None
        except Exception:
            raise HTTPException(503, "Download issuance unavailable; no link released") from None
        return ("<h1>Private installer download</h1><p>This link expires in "
            + str(decision.ttl_seconds) + " seconds. Keep it private.</p><p><a rel='noreferrer' href='"
            + html.escape(url, quote=True) + "'>Download TEC EPR Clinic Edition 1.0.0</a></p>"
            "<p>Verify the archive SHA-256 and publisher signature before installation.</p><p>SHA-256: <code>"
            + decision.release.sha256 + "</code></p><p>No software licence is issued by this download.</p>"
            "<a href='/customer'>Return to customer access</a>")

    try:
        from .onboarding_ui import register
        from .onboarding import requests as customer_requests
        from .appoint_admins import lookup_user
    except ImportError:
        from onboarding_ui import register
        from onboarding import requests as customer_requests
        from appoint_admins import lookup_user
    onboarding_service = register(app, config, engine, entitlements, current, protected_form,
        identity_lookup or (lambda subject: lookup_user(config.api_key, subject)))
    return app


def from_environment():
    if os.environ.get("APP_ENV") != "staging":
        raise RuntimeError("This candidate is staging-only")
    url = os.environ.get("COMMERCIAL_DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        raise RuntimeError("Dedicated commercial PostgreSQL URL required")
    url = url.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
    config = Config(os.environ["GATEWAY_ORIGIN"], os.environ["WORKOS_CLIENT_ID"],
                    os.environ["WORKOS_API_KEY"], os.environ.get("GATEWAY_AUTH_ENABLED") == "true",
                    os.environ.get("GATEWAY_MFA_ENABLED") == "true",
                    tuple(s.strip() for s in os.environ.get("GATEWAY_ENROLLMENT_SUBJECTS", "").split(",") if s.strip()),
                    os.environ.get("GATEWAY_ONBOARDING_ENABLED") == "true",
                    os.environ.get("GATEWAY_DOWNLOADS_ENABLED") == "true",
                    os.environ.get("GATEWAY_RELEASE_APPROVED") == "true")
    signer = None
    if config.downloads_enabled and config.release_approved:
        try:
            from .downloads import R2Signer
        except ImportError:
            from downloads import R2Signer
        signer = R2Signer(os.environ.get('R2_ACCESS_KEY_ID',''), os.environ.get('R2_SECRET_ACCESS_KEY',''))
    return create_app(config, create_engine(url, pool_pre_ping=True, hide_parameters=True), download_signer=signer)
