import html
import secrets
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
try:
    from .ui import page as view
except ImportError:
    from ui import page as view
try:
    from .onboarding import requests, Onboarding
    from .entitlements import grants, tenants, memberships, Denied
except ImportError:
    from onboarding import requests, Onboarding
    from entitlements import grants, tenants, memberships, Denied


class AdministratorVerificationRequired(HTTPException):
    def __init__(self):
        super().__init__(403, "Administrator verification required")


def register(app, config, engine, access, current, protected_form, lookup):
    service = Onboarding(access, lookup)
    esc = lambda value: html.escape(str(value), quote=True)

    @app.exception_handler(AdministratorVerificationRequired)
    async def verification_required(request, error):
        return HTMLResponse(view("Administrator verification required",
            '<section class="card"><div class="notice warn">'
            'This action was not performed. Administrator verification lasts five minutes.</div>'
            '<p>Use Back to return to your form. In a second tab in the same browser, '
            'open My account and verify your authenticator, then submit again. Do not sign out.</p>'
            '<p><a class="button secondary" href="/account" target="_blank" '
            'rel="noopener noreferrer">My account — new tab</a></p>'
            '<p>If fresh verification does not resolve this, ask the owner to '
            'check your administrator appointment.</p></section>',
            eyebrow="SECURITY VERIFICATION"), status_code=403)

    def enabled():
        if not config.onboarding_enabled:
            raise HTTPException(503, 'Customer onboarding is disabled')

    def admin(request):
        row = current(request)
        enabled()
        try:
            with engine.begin() as c:
                access._actor(c, row['token_hash'], int(access.clock()))
        except Denied:
            raise AdministratorVerificationRequired() from None
        return row

    @app.get('/admin/customers', response_class=HTMLResponse)
    def page(request: Request):
        row = admin(request)
        with engine.connect() as c:
            records = c.execute(select(requests, grants.c.state, grants.c.proposer, grants.c.starts,
                grants.c.expires, grants.c.contract_reference, grants.c.approval_reference)
                .join(grants, grants.c.id == requests.c.id)
                .order_by(requests.c.created.desc(), requests.c.id).limit(100)).mappings().all()
        output = ("<section class='card'><h2>Propose customer access</h2>"
            "<p>Use synthetic organisations for staging validation. "
            "Do not enter patient information. A second appointed administrator must "
            "independently approve each customer.</p>"
            "<div class='notice warn'>Administrator verification lasts five minutes. "
            "If necessary, <a href='/account' target='_blank' rel='noopener noreferrer'>"
            "verify in a second tab</a> before submitting this form. Keep the form open "
            "and do not sign out.</div>"
            "<form method='post' action='/admin/customers/propose'>"
            "<input type='hidden' name='csrf' value='" + row['csrf'] + "'>"
            "<input type='hidden' name='request_id' value='" + secrets.token_hex(16) + "'>")
        for name, label, kind, size in (
            ('organisation','Organisation','text',160), ('subject','Customer WorkOS Account ID','text',160),
            ('email','Verified customer email','email',254),
            ('contract_reference','Contract or pilot approval reference','text',160),
            ('approval_reference','Review evidence reference','text',160),
            ('starts','Access starts (UTC)','datetime-local',32),
            ('expires','Access expires (UTC)','datetime-local',32)):
            output += ("<p><label>"+label+" <input required name='"+name+"' type='"+kind
                       +"' maxlength='"+str(size)+"'></label></p>")
        output += ("<button>Submit for independent approval</button></form></section>"
                   "<h2>Recent customer requests</h2>")
        if not records:
            output += '<p>No customer requests submitted.</p>'
        for r in records:
            output += '<section class="card"><h3>'+esc(r['organisation'])+'</h3><dl>'
            for key in ('id','subject','email','state','proposer','contract_reference','approval_reference','starts','expires'):
                value = datetime.fromtimestamp(r[key], timezone.utc).strftime('%d %b %Y %H:%M UTC') if key in ('starts','expires') else r[key]
                output += '<dt>'+esc(key.replace('_',' ').title())+'</dt><dd>'+esc(value)+'</dd>'
            output += '</dl>'
            if r['state']=='pending' and r['proposer']!=row['subject']:
                output += ("<form method='post' action='/admin/customers/"+esc(r['id'])+"/approve'>"
                    "<input type='hidden' name='csrf' value='"+row['csrf']+"'><button>Approve customer access</button></form>")
            if r['state']!='revoked':
                output += ("<form method='post' action='/admin/grants/"+esc(r['id'])+"/revoke'>"
                    "<input type='hidden' name='csrf' value='"+row['csrf']+"'><button>Revoke request or grant</button></form>")
            output += '</section>'
        return view("Customer onboarding and review",
            output + '<div class="actions"><a class="button secondary" href="/admin">Approval dashboard</a>'
                     '<a class="button secondary" href="/account">My account</a></div>',
            eyebrow="ADMINISTRATOR WORKSPACE",
            intro="Propose secure access, review pending requests and manage entitlements with independent approval.")

    @app.post('/admin/customers/propose')
    async def propose(request: Request):
        row = admin(request)
        fields = await protected_form(request, row)
        try:
            values = {k:fields.get(k,[''])[0] for k in ('request_id','organisation','subject','email',
                                                       'contract_reference','approval_reference','starts','expires')}
            for k in ('starts','expires'):
                # HTML datetime-local is explicitly labelled UTC; no client timezone inference.
                value = datetime.fromisoformat(values[k])
                if value.tzinfo is not None:
                    raise ValueError('Unexpected timezone')
                values[k] = int(value.replace(tzinfo=timezone.utc).timestamp())
            service.propose(row['token_hash'], **values)
        except (ValueError, OverflowError):
            raise HTTPException(400, 'Enter valid UTC start and expiry dates') from None
        except Denied as error:
            raise HTTPException(403, str(error)) from None
        return RedirectResponse('/admin/customers',303)

    @app.post('/admin/customers/{request_id}/approve')
    async def approve(request_id: str, request: Request):
        row = admin(request)
        await protected_form(request,row)
        try:
            service.approve(row['token_hash'],request_id)
        except Denied as error:
            raise HTTPException(403,str(error)) from None
        return RedirectResponse('/admin/customers',303)

    @app.get('/customer', response_class=HTMLResponse)
    def customer(request: Request):
        row = current(request)
        enabled()
        with engine.connect() as c:
            records = c.execute(select(grants.c.id,grants.c.state,grants.c.starts,grants.c.expires,
                        requests.c.organisation)
                .select_from(memberships.join(tenants,tenants.c.id==memberships.c.tenant_id)
                    .join(grants,grants.c.tenant_id==tenants.c.id)
                    .outerjoin(requests,requests.c.id==grants.c.id))
                .where(memberships.c.subject==row['subject'],memberships.c.active.is_(True),tenants.c.active.is_(True))
                .order_by(grants.c.id).limit(100)).mappings().all()
        output = '<div class="grid">'
        if not records:
            output += ('<section class="card"><span class="stat pending">Awaiting approval</span>'
                '<h2>No active customer entitlements</h2>'
                '<p>No approved customer membership is available for your account. '
                'If you are expecting access, contact the TCL administrator managing your organisation.</p>'
                '</section>')
        for r in records:
            now = int(access.clock())
            status = r['state']
            if status == 'approved':
                status = 'scheduled' if now < r['starts'] else ('expired' if now >= r['expires'] else 'approved')
            badge = 'stat' if status == 'approved' else 'stat pending' if status in ('pending','scheduled') else 'stat revoked'
            output += ('<section class="card"><span class="' + badge + '">'
                + esc(status.title()) + '</span><h2>'
                + esc(r['organisation'] or 'Customer organisation') + '</h2>'
                '<span class="kicker">TEC EPR CLINIC EDITION '+esc(config.release_id.rsplit('-',1)[-1])+'</span>'
                '<p class="fine">Grant reference</p><code class="code">'
                + esc(r['id']) + '</code>')
            if status == 'approved' and config.downloads_enabled and config.release_approved:
                output += ("<p>Your approved release is available through a short-lived "
                    "private download link.</p><form method='post' action='/api/downloads'>"
                    "<input type='hidden' name='csrf' value='" + esc(row['csrf'])
                    + "'><input type='hidden' name='grant_id' value='" + esc(r['id'])
                    + "'><button>Request secure download</button></form>")
            else:
                output += ('<p class="notice warn">A private download is unavailable for '
                    'this entitlement or is currently disabled.</p>')
            output += '</section>'
        output += '</div>'
        output += ('<section class="card"><h2>Release and licence information</h2>'
            '<p>Downloading an archive does not activate or issue a licence. '
            'Your release is subject to approved access and separate licensing.</p>')
        if not (config.downloads_enabled and config.release_approved):
            output += '<p class="notice">Private download issuance is currently disabled.</p>'
        output += '<a class="button secondary" href="/account">My account</a></section>'
        return view("My customer access", output,
            eyebrow="YOUR SOFTWARE ENTITLEMENTS",
            intro="Review your approved release access and request authorised private downloads.")

    return service
