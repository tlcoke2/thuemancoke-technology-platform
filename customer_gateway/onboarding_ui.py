import html
import secrets
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
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
        return HTMLResponse("<h1>Administrator verification required</h1>"
            "<p>This action was not performed. Administrator verification lasts five minutes.</p>"
            "<p>Use Back to return to your form. In a second tab in the same browser, "
            "open My account and verify your authenticator, then submit again. Do not sign out.</p>"
            "<p><a href='/account' target='_blank' rel='noopener noreferrer'>My account — new tab</a></p>"
            "<p>If fresh verification does not resolve this, ask the owner to check your administrator appointment.</p>",
            status_code=403)

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
        output = ("<h1>Customer onboarding — Staging</h1><p>Use synthetic organisations for validation. "
            "No patient records belong here. A second administrator must approve each request. "
            "Grant approval does not issue a software licence.</p>"
            "<p>Administrator verification lasts five minutes. If you need more time, "
            "<a href='/account' target='_blank' rel='noopener noreferrer'>verify your authenticator in a second tab</a> "
            "before submitting. Keep this form open and do not sign out.</p>"
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
        output += "<button>Submit for independent approval</button></form><h2>Recent customer requests</h2>"
        if not records:
            output += '<p>No customer requests submitted.</p>'
        for r in records:
            output += '<section><h3>'+esc(r['organisation'])+'</h3><dl>'
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
        return output+"<p><a href='/admin'>Approval dashboard</a> · <a href='/account'>My account</a></p>"

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
        output='<h1>My customer access — Staging</h1>'
        if not records:
            output+='<p>No approved customer membership is available for your account.</p>'
        for r in records:
            output+='<section><h2>'+esc(r['organisation'] or 'Customer organisation')+'</h2>'
            now=int(access.clock())
            status = r['state']
            if status=='approved':
                status='scheduled' if now < r['starts'] else ('expired' if now >= r['expires'] else 'approved')
            output+='<p>Grant: '+esc(r['id'])+' — '+esc(status)+'</p>'
            if status=='approved' and config.downloads_enabled and config.release_approved:
                output+=("<form method='post' action='/api/downloads'><input type='hidden' name='csrf' value='"
                    +row['csrf']+"'><input type='hidden' name='grant_id' value='"+esc(r['id'])
                    +"'><button>Request private download</button></form>")
            output+='</section>'
        return output+("<p>No software licence has been issued.</p>" if config.downloads_enabled and config.release_approved else "<p>Download issuance remains disabled. No software licence has been issued.</p>")+"<a href='/account'>My account</a>"

    return service
