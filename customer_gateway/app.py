import base64
import hashlib
import html
import os
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


def create_app(config, engine, provider=None, clock=time.time, mfa_provider=None):
    provider = provider or WorkOS(config)
    try:
        from .mfa import StepUp, WorkOSMFA, MFAError, elevations, metadata as access_metadata
    except ImportError:
        from mfa import StepUp, WorkOSMFA, MFAError, elevations, metadata as access_metadata
    step_up = StepUp(engine, sessions, audit, mfa_provider or WorkOSMFA(config.api_key), clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security(request, call_next):
        # No dependence on attacker-controlled forwarded host for redirects or cookies.
        if request.url.hostname != urlsplit(config.origin).hostname and request.url.path != "/health":
            return HTMLResponse("Invalid host", status_code=400)
        response = await call_next(request)
        # HTML form POSTs under no-referrer can send Origin: null. Only the
        # account page needs same-origin; keep callback codes fully suppressed.
        policy = "same-origin" if request.url.path in ("/account", "/auth/mfa") else "no-referrer"
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": policy,
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            "Strict-Transport-Security": "max-age=31536000"})
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
                "downloadsEnabled": False, "mfaStepUpEnabled": config.mfa_enabled}

    @app.get("/ready")
    def ready():
        with engine.connect() as c:
            c.execute(select(sessions.c.token_hash).limit(1))
            if config.mfa_enabled:
                for table in access_metadata.sorted_tables:
                    c.execute(select(table).limit(0))
        return {"ready": True}

    @app.get("/", response_class=HTMLResponse)
    def home():
        return "<h1>TCL Customer Gateway — Staging</h1><p>Sign-in testing only. Downloads and licences are unavailable.</p><a href='/auth/login'>Sign in</a>"

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
        if config.mfa_enabled:
            with engine.connect() as c:
                elevation = c.execute(select(elevations.c.expires).where(
                    elevations.c.session_hash == row['token_hash'],
                    elevations.c.subject == row['subject'],
                    elevations.c.expires > int(clock()))).first()
            mfa_html = ("<p>Additional verification: " + ("verified for this session" if elevation else "required")
                + "</p><p>Account ID: <code>" + html.escape(row['subject']) + "</code></p>"
                + "<form action='/auth/mfa/start' method='post'><input type='hidden' name='csrf' value='"
                + row['csrf'] + "'><button>Verify authenticator</button></form>")
        return ("<h1>Sign-in successful</h1><p>Your email is verified. Customer access awaits approval.</p>"
                "<p>No download, administrator privilege or licence has been granted.</p>"
                + mfa_html + "<form action='/auth/logout' method='post'><input type='hidden' name='csrf' value='"
                +row["csrf"]+"'><button>Sign out of this gateway</button></form>")

    async def protected_form(request, row):
        if request.headers.get("origin") != config.origin:
            raise HTTPException(403, "Origin rejected")
        if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
            raise HTTPException(415, "Form required")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 512:
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
        response = RedirectResponse("/", 303)
        response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")
        return response

    @app.post("/api/downloads")
    def downloads(request: Request):
        current(request)
        raise HTTPException(403, "Downloads are not enabled")

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
                    os.environ.get("GATEWAY_MFA_ENABLED") == "true")
    return create_app(config, create_engine(url, pool_pre_ping=True, hide_parameters=True))
