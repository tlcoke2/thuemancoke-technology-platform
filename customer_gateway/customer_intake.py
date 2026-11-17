"""Authenticated commercial requests; this module never grants access or signs licences."""
import html
import re
import secrets
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import MetaData, Table, Column, String, Integer, select, insert, func, text
try:
    from .ui import page
except ImportError:
    from ui import page

metadata = MetaData()
requests = Table('gateway_self_service_requests', metadata,
    Column('id', String(32), primary_key=True),
    Column('subject', String(160), nullable=False, index=True),
    Column('organisation', String(160), nullable=False),
    Column('country', String(80), nullable=False),
    Column('intent', String(24), nullable=False),
    Column('state', String(24), nullable=False),
    Column('created', Integer, nullable=False))
INTENTS = {'demo':'Demo licence request', 'subscription':'Subscription enquiry',
           'outright':'Outright purchase quotation', 'licence':'Installation licence request'}

def register(app, config, engine, current, protected_form, sessions, clock, access):
    esc = lambda v: html.escape(str(v), quote=True)

    @app.get('/start', response_class=HTMLResponse)
    def start():
        return page('Your software journey starts here',
            '<div class="grid"><section class="card panel-gradient"><span class="kicker">NEW CUSTOMERS</span>'
            '<h2>Create your secure account</h2><p>Register with your email address, verify it and set up your sign-in credentials with our identity provider.</p>'
            '<a class="button" href="/auth/login?screen_hint=sign-up">Create customer account</a></section>'
            '<section class="card"><h2>Already registered?</h2><p>Sign in to request a demo, discuss a subscription, request an outright purchase quotation or access your approved downloads.</p>'
            '<a class="button" href="/account">Sign in / my account</a></section></div>'
            '<section class="card"><h2>Four straightforward steps</h2><ol>'
            '<li>Create and verify your account.</li><li>Select your software request and organisation.</li>'
            '<li>Review your request status and any agreed commercial terms.</li>'
            '<li>Download your approved release, install it and obtain an installation-bound licence.</li></ol>'
            '<p><a class="button secondary" href="/customer/requests">Choose demo, subscription or outright purchase</a></p>'
            '<p>Private requests require review. An account or payment alone does not authorise clinical use or issue a licence. '
            'Do not submit patient records, passwords or private signing keys.</p></section>',
            eyebrow='TEC EPR CUSTOMER CENTRE', intro='One secure account for software requests, approved downloads and licence enquiries.')

    @app.get('/customer/requests', response_class=HTMLResponse)
    def request_page(request: Request):
        row=current(request)
        with engine.connect() as c:
            records=c.execute(select(requests).where(requests.c.subject==row['subject'])
                .order_by(requests.c.created.desc()).limit(20)).mappings().all()
        choices=''.join('<option value="'+k+'">'+v+'</option>' for k,v in INTENTS.items())
        body='<section class="card"><h2>Tell us what you need</h2><p>Use business details only. Outright purchase pricing is provided by private quotation.</p>'
        body+='<form method="post" action="/customer/requests"><input type="hidden" name="csrf" value="'+esc(row['csrf'])+'">'
        body+='<input type="hidden" name="request_id" value="'+secrets.token_hex(16)+'">'
        body+='<label>Organisation<input name="organisation" maxlength="160" minlength="2" required autocomplete="organization"></label>'
        body+='<label>Country<input name="country" maxlength="80" minlength="2" required autocomplete="country-name"></label>'
        body+='<label>Request type<select name="intent">'+choices+'</select></label>'
        body+='<p>Requests are recorded against your verified account. No patient information or installation files are required at this stage.</p>'
        body+='<button>Submit private request</button></form></section><section class="card"><h2>Your requests</h2>'
        if not records: body+='<p>You have no requests yet.</p>'
        for r in records:
            body+='<h3>'+esc(INTENTS[r['intent']])+'</h3><p>'+esc(r['organisation'])+' — '+esc(r['state'])+'</p><code class="code">'+esc(r['id'])+'</code>'
        body+='</section><p><a href="/customer">Approved downloads</a> · <a href="https://thuemancokelimited.com/software.html#pricing">View subscription pricing</a> · <a href="/account">My account</a></p>'
        return page('My software requests',body,intro='Submit once and track your request here. Requests do not grant download or licence access.')

    @app.post('/customer/requests')
    async def submit(request: Request):
        row=current(request)
        fields=await protected_form(request,row)
        values={k:fields.get(k,[''])[0].strip() for k in ('request_id','organisation','country','intent')}
        if (not re.fullmatch('[a-f0-9]{32}',values['request_id']) or values['intent'] not in INTENTS
            or not 2<=len(values['organisation'])<=160 or not 2<=len(values['country'])<=80
            or any(ord(ch)<32 for k in ('organisation','country') for ch in values[k])):
            raise HTTPException(400,'Enter valid business details and request type')
        now=int(clock())
        with engine.begin() as c:
            # Serialize per identity through the existing session row; no client-supplied identity is trusted.
            if c.dialect.name == 'postgresql':
                c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:subject, 0))'), {'subject':row['subject']})
            active=c.execute(select(sessions).where(sessions.c.token_hash==row['token_hash'],sessions.c.expires>now).with_for_update()).first()
            if not active: raise HTTPException(401,'Sign in required')
            old=c.execute(select(requests).where(requests.c.id==values['request_id'])).mappings().first()
            if old:
                if old['subject']!=row['subject'] or any(old[k]!=values[k] for k in ('organisation','country','intent')):
                    raise HTTPException(409,'Request identifier already used')
                return RedirectResponse('/customer/requests',303)
            if c.scalar(select(func.count()).select_from(requests).where(requests.c.subject==row['subject'],requests.c.created>now-86400))>=5:
                raise HTTPException(429,'Daily request limit reached; review your existing requests')
            c.execute(insert(requests).values(id=values['request_id'],subject=row['subject'],organisation=values['organisation'],
                country=values['country'],intent=values['intent'],state='received',created=now))
        return RedirectResponse('/customer/requests',303)

    @app.get('/admin/software-requests', response_class=HTMLResponse)
    def inbox(request: Request):
        row=current(request)
        try:
            with engine.begin() as c:
                access._actor(c,row['token_hash'],int(clock()))
                records=c.execute(select(requests).order_by(requests.c.created.desc()).limit(100)).mappings().all()
        except Exception:
            raise HTTPException(403,'Appointed administrator and recent MFA required') from None
        body='<section class="card"><h2>Private customer requests</h2><p>Verify identity and commercial terms before using the existing customer approval workflow. No access is granted by this inbox.</p>'
        for r in records:
            body+='<h3>'+esc(INTENTS[r['intent']])+'</h3><p>'+esc(r['organisation'])+' — '+esc(r['country'])+'</p><dl>'
            for k in ('id','subject','state'):
                body+='<dt>'+esc(k.title())+'</dt><dd>'+esc(r[k])+'</dd>'
            body+='</dl>'
        return page('Software request inbox',body+'</section><p><a href="/admin/customers">Customer approval workspace</a></p>')
