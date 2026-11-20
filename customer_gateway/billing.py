"""Hosted subscription checkout and a durable, signature-verified billing ledger.

Payments never bypass the independent access approval or offline licence signer.
"""
import html
import json
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import stripe
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy import (MetaData, Table, Column, String, Integer, Boolean, insert,
                        select, update, func, text)
try:
    from .ui import page
    from .entitlements import Denied
except ImportError:
    from ui import page
    from entitlements import Denied

API_VERSION = '2026-10-28.endive'
EVENTS = ('checkout.session.completed', 'checkout.session.async_payment_succeeded',
          'checkout.session.async_payment_failed', 'checkout.session.expired',
          'customer.subscription.created', 'customer.subscription.updated',
          'customer.subscription.deleted', 'invoice.paid', 'invoice.payment_failed',
          'charge.refunded', 'charge.dispute.created', 'radar.early_fraud_warning.created')
RISK_EVENTS = frozenset(EVENTS[-3:])
metadata = MetaData()
orders = Table('gateway_billing_orders', metadata,
    Column('id', String(32), primary_key=True),
    Column('subject', String(160), nullable=False, index=True),
    Column('plan', String(32), nullable=False),
    Column('checkout_id', String(160), unique=True),
    Column('customer_id', String(160)),
    Column('subscription_id', String(160), unique=True),
    Column('state', String(32), nullable=False),
    Column('risk_hold', Boolean, nullable=False, default=False),
    Column('created', Integer, nullable=False),
    Column('updated', Integer, nullable=False))
receipts = Table('gateway_billing_events', metadata,
    Column('id', String(160), primary_key=True),
    Column('event', String(80), nullable=False),
    Column('object_id', String(160), nullable=False),
    Column('created', Integer, nullable=False))

@dataclass(frozen=True)
class BillingConfig:
    enabled: bool = False
    key: str = ''
    webhook_secret: str = ''
    live: bool = False
    account: str = ''
    verified: bool = False

    @classmethod
    def environment(cls):
        c = cls(os.getenv('GATEWAY_BILLING_ENABLED') == 'true',
                os.getenv('STRIPE_RESTRICTED_KEY', ''), os.getenv('STRIPE_WEBHOOK_SECRET', ''),
                os.getenv('STRIPE_LIVEMODE') == 'true', os.getenv('STRIPE_EXPECTED_ACCOUNT', ''),
                os.getenv('GATEWAY_BILLING_ACCEPTANCE_VERIFIED') == 'true')
        if c.enabled:
            if not c.live and not os.getenv('STRIPE_SANDBOX_CATALOG_JSON'):
                raise RuntimeError('Separate sandbox catalogue required')
            if (not c.verified or not c.key.startswith('rk_live_' if c.live else 'rk_test_')
                    or not c.webhook_secret.startswith('whsec_') or not c.account.startswith('acct_')):
                raise RuntimeError('Billing acceptance and protected Stripe configuration required')
        return c


def identifier(value):
    return value.get('id') if isinstance(value, dict) else value


def subscription_of(invoice):
    parent = invoice.get('parent') or {}
    return identifier((parent.get('subscription_details') or {}).get('subscription')) if parent.get('type') == 'subscription_details' else None


class StripeBilling:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = stripe.StripeClient(cfg.key, stripe_version=API_VERSION,
                                          max_network_retries=2)

    def check_account(self):
        account = self.client.v1.accounts.retrieve_current()
        if account.id != self.cfg.account or (self.cfg.live and not account.charges_enabled):
            raise ValueError('Stripe account mismatch')

    def create(self, order, plan, origin):
        self.check_account()
        price = self.client.v1.prices.retrieve(plan['stripeMonthlyPriceId'])
        if (price.unit_amount != plan['monthlyMinor'] or price.currency != 'jmd'
                or price.tax_behavior != 'exclusive' or not price.active
                or price.livemode != self.cfg.live or price.product != plan['stripeProductId']
                or price.recurring.interval != 'month'):
            raise ValueError('Catalogue price mismatch')
        return self.client.v1.checkout.sessions.create({
            'mode': 'subscription', 'line_items': [{'price': price.id, 'quantity': 1}],
            'automatic_tax': {'enabled': True}, 'tax_id_collection': {'enabled': True},
            'client_reference_id': order['id'],
            'success_url': origin + '/customer/billing?checkout=returned',
            'cancel_url': origin + '/customer/billing?checkout=cancelled',
            'integration_identifier': 'tcl_gateway_' + ''.join(chr(97 + int(ch, 16)) for ch in order['id'][:8]),
            'expires_at': order['created'] + 1800,
        }, options={'idempotency_key': 'tcl-checkout-' + order['id']})

    def verify(self, raw, signature):
        return stripe.Webhook.construct_event(raw, signature, self.cfg.webhook_secret, tolerance=300).to_dict()

    def checkout(self, sid):
        return self.client.v1.checkout.sessions.retrieve(sid).to_dict()

    def subscription(self, sid):
        return self.client.v1.subscriptions.retrieve(sid, {'expand': ['latest_invoice']}).to_dict()

    def checkout_for_subscription(self, sid):
        return [s.to_dict() for s in self.client.v1.checkout.sessions.list({'subscription': sid, 'limit': 100}).auto_paging_iter()]

    def risk_subscriptions(self, obj):
        pi = identifier(obj.get('payment_intent'))
        if not pi and obj.get('charge'):
            charge = self.client.v1.charges.retrieve(identifier(obj['charge']))
            pi = identifier(charge.get('payment_intent'))
        if not pi:
            return []
        subscriptions = set()
        payments = self.client.v1.invoice_payments.list({'payment': {'type': 'payment_intent', 'payment_intent': pi}, 'status': 'paid', 'limit': 100})
        for payment in payments.auto_paging_iter():
            inv = self.client.v1.invoices.retrieve(identifier(payment.invoice)).to_dict()
            sid = subscription_of(inv)
            if sid:
                subscriptions.add(sid)
        return sorted(subscriptions)

    def portal(self, customer, origin):
        configuration = os.getenv('STRIPE_PORTAL_CONFIGURATION', '')
        if not configuration.startswith('bpc_'):
            raise ValueError('Pinned customer portal configuration required')
        return self.client.v1.billing_portal.sessions.create({'customer': customer, 'configuration': configuration, 'return_url': origin + '/customer/billing'})


class Ledger:
    def __init__(self, engine, cfg, provider, clock, access):
        self.engine, self.cfg, self.provider, self.clock, self.access = engine, cfg, provider, clock, access

    def require_download_clear(self, subject):
        if not self.cfg.enabled:
            return
        with self.engine.connect() as c:
            blocked = c.execute(select(orders.c.id).where(orders.c.subject == subject,
                orders.c.risk_hold.is_(True))).first()
            latest = c.scalar(select(orders.c.state).where(orders.c.subject == subject, orders.c.subscription_id.is_not(None)).order_by(orders.c.created.desc(), orders.c.id.desc()).limit(1))
        if blocked or latest in ('unpaid', 'canceled', 'incomplete_expired', 'paused'):
            raise HTTPException(403, 'Billing review required before another download')

    def event(self, event):
        if event.get('livemode') is not self.cfg.live or event.get('account') not in (None, self.cfg.account):
            raise ValueError('Webhook environment mismatch')
        eid, kind = event.get('id', ''), event.get('type', '')
        obj = (event.get('data') or {}).get('object') or {}
        if not re.fullmatch(r'evt_[A-Za-z0-9_]{1,150}', eid) or not isinstance(obj.get('id'), str):
            raise ValueError('Malformed event')
        if kind not in EVENTS:
            return
        now = int(self.clock())
        # PostgreSQL serializes duplicate deliveries before external reconciliation.
        with self.engine.begin() as c:
            if c.dialect.name == 'postgresql':
                c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))'), {'id': eid})
            if c.execute(select(receipts.c.id).where(receipts.c.id == eid)).first():
                return
            checkout = None
            if kind.startswith('checkout.session.'):
                checkout = self.provider.checkout(obj['id'])
                sids = [identifier(checkout.get('subscription'))] if checkout.get('subscription') else []
            elif kind.startswith('customer.subscription.'):
                sids = [obj['id']]
            elif kind.startswith('invoice.'):
                sid = subscription_of(obj)
                sids = [sid] if sid else []
            else:
                sids = self.provider.risk_subscriptions(obj)
            matches = []
            mapping_pending = False
            if checkout:
                row = c.execute(select(orders).where(orders.c.checkout_id == checkout['id']).with_for_update()).mappings().first()
                if not row and checkout.get('client_reference_id'):
                    mapping_pending = c.execute(select(orders.c.id).where(orders.c.id == checkout['client_reference_id'])).first() is not None
                if row:
                    matches.append((row, sids[0] if sids else None, checkout))
            else:
                for sid in sids:
                    row = c.execute(select(orders).where(orders.c.subscription_id == sid).with_for_update()).mappings().first()
                    session = None
                    if not row:
                        # Out-of-order invoice/subscription events: traverse first-class resources,
                        # never trust caller-supplied email, metadata or subject for ownership.
                        for candidate in self.provider.checkout_for_subscription(sid):
                            if candidate.get('client_reference_id'):
                                mapping_pending = mapping_pending or c.execute(select(orders.c.id).where(orders.c.id == candidate['client_reference_id'])).first() is not None
                            row = c.execute(select(orders).where(orders.c.checkout_id == candidate['id']).with_for_update()).mappings().first()
                            if row:
                                session = candidate
                                break
                    if row:
                        matches.append((row, sid, session))
            for row, sid, session in matches:
                if session and (session.get('livemode') is not self.cfg.live or session.get('mode') != 'subscription'
                                or session.get('client_reference_id') != row['id']):
                    raise ValueError('Checkout ownership mismatch')
                risk = row['risk_hold'] or kind in RISK_EVENTS
                values = {'updated': now, 'risk_hold': risk}
                if sid:
                    sub = self.provider.subscription(sid)
                    if sub.get('livemode') is not self.cfg.live:
                        raise ValueError('Subscription environment mismatch')
                    values.update(subscription_id=sid, customer_id=identifier(sub.get('customer')),
                                  state='risk_review' if risk else (sub['status'] if sub['status'] != 'active' or (sub.get('latest_invoice') or {}).get('status') == 'paid' else 'pending_payment'))
                elif session:
                    values.update(state='expired' if session.get('status') == 'expired' else 'pending_payment')
                if risk:
                    values['state'] = 'risk_review'
                c.execute(update(orders).where(orders.c.id == row['id']).values(**values))
                self.access._event(c, 'billing_' + ('risk_review' if risk else 'reconciled'), row['subject'], row['id'], now)
            # Unmapped related events must be retried: a webhook can arrive while
            # checkout creation is still committing the first-class session ID.
            if not matches and mapping_pending:
                raise RuntimeError('Billing ownership not yet mapped')
            c.execute(insert(receipts).values(id=eid, event=kind, object_id=obj['id'], created=now))


def register(app, config, engine, current, protected_form, clock, access, cfg=None, provider=None):
    cfg = cfg or BillingConfig.environment()
    provider = provider or (StripeBilling(cfg) if cfg.enabled else None)
    catalog = json.loads(Path(__file__).with_name('commercial_catalog.json').read_text())
    plans = {p['code']: p for p in catalog['pricing']['plans']}
    # Sandboxes have their own Products/Prices. Never reuse live IDs in testing.
    overrides = os.getenv('STRIPE_SANDBOX_CATALOG_JSON', '') if not cfg.live else ''
    if overrides:
        sandbox = json.loads(overrides)
        if set(sandbox) != set(plans):
            raise RuntimeError('Complete sandbox catalogue required')
        for code, ids in sandbox.items():
            if set(ids) != {'product', 'price'} or not ids['price'].startswith('price_') or not ids['product'].startswith('prod_'):
                raise RuntimeError('Invalid sandbox catalogue IDs')
            plans[code] = dict(plans[code], stripeProductId=ids['product'], stripeMonthlyPriceId=ids['price'])
    ledger = Ledger(engine, cfg, provider, clock, access)
    esc = lambda v: html.escape(str(v), quote=True)

    def plan_cards(row=None):
        body = '<div class="grid">'
        for code, p in plans.items():
            request_intent = 'paylink_' + ('essentials' if code == 'clinic_essentials' else code)
            body += '<section class="card"><span class="kicker">TEC EPR CLINIC EDITION</span><h2>' + esc(p['name']) + '</h2>'
            body += '<p><strong>JMD ' + format(p['monthlyMinor']/100, ',.2f') + '</strong> per month, plus applicable tax.</p>'
            body += '<p>Implementation: ' + ('from ' if p.get('startingPrice') else '') + 'JMD ' + format(p['implementationMinor']/100, ',.2f') + ', separately agreed. '
            body += ('All modules; larger deployments require a private quotation.' if code == 'enterprise' else 'Modules, support and implementation scope are confirmed in your order.') + '</p>'
            if cfg.enabled and row:
                body += '<form method="post" action="/customer/billing/checkout"><input type="hidden" name="csrf" value="' + esc(row['csrf']) + '"><input type="hidden" name="order_id" value="' + secrets.token_hex(16) + '"><input type="hidden" name="plan" value="' + code + '"><label><input type="checkbox" name="terms" value="accepted" required> I accept the agreed software order, separate implementation costs and monthly recurring billing.</label><button>Enter payment details securely</button></form>'
            elif cfg.enabled:
                body += '<p><a class="button" href="/customer/billing">Sign in for secure checkout</a></p>'
            else:
                body += '<p class="notice">Card checkout is not available yet. Payment-link requests are open.</p>'
            body += '<p><a class="button secondary" href="/customer/requests?intent=' + request_intent + '">Request a payment link</a></p></section>'
        return body + '</div>'

    @app.get('/payments', response_class=HTMLResponse)
    def payment_options():
        return page('Choose how you would like to pay',
            '<section class="card"><h2>Secure checkout or a private payment link</h2><p>Choose your subscription below. Sign in or register to request a payment link for your organisation. Payment details are entered only on Stripe’s secure payment page when checkout is available.</p><p><a class="button" href="/auth/login?screen_hint=sign-up">Create customer account</a> <a class="button secondary" href="/customer/billing">Sign in / my billing</a></p></section>'
            + plan_cards() + '<section class="card"><h2>Demo or outright purchase?</h2><p>Request a demo licence, outright purchase quotation or a larger Enterprise deployment through your verified customer account.</p><a class="button secondary" href="/customer/requests?intent=outright">Request a private quotation</a><p>Payment alone does not approve clinical use or issue an installation licence. Never enter card details, patient information or private keys in a request.</p></section>',
            eyebrow='TCL CUSTOMER PAYMENTS', intro='Clear pricing, secure payment and requests tracked in your customer account.')

    @app.get('/customer/billing', response_class=HTMLResponse)
    def billing_page(request: Request):
        row = current(request)
        body = '<section class="card"><h2>Your payment options</h2><p>Prices are in Jamaican dollars before applicable tax. Implementation is priced separately under an agreed order. Outright purchases and larger Enterprise deployments require a quotation. Payment does not replace clinical approval or installation licensing.</p></section>' + plan_cards(row)
        if cfg.enabled:
            with engine.connect() as c:
                records = c.execute(select(orders).where(orders.c.subject == row['subject']).order_by(orders.c.created.desc()).limit(20)).mappings().all()
            body += '<section class="card"><h2>Your billing status</h2>'
            for r in records:
                body += '<p>' + esc(plans[r['plan']]['name']) + ' — ' + esc(r['state'].replace('_', ' ')) + '<br>Order: ' + esc(r['id']) + '</p>'
            if any(r['customer_id'] for r in records):
                body += '<form method="post" action="/customer/billing/portal"><input type="hidden" name="csrf" value="' + esc(row['csrf']) + '"><button>Manage subscription or payment method</button></form>'
            body += '</section>'
        body += '<section class="card"><p><a href="/customer/requests">My payment-link and software requests</a> · <a href="/customer">Approved downloads</a></p></section>'
        return page('My subscriptions and payments', body, intro='Secure payment, order tracking and a separate installation-bound licence.')

    @app.post('/customer/billing/checkout')
    async def checkout(request: Request):
        row = current(request)
        fields = await protected_form(request, row)
        if not cfg.enabled:
            raise HTTPException(503, 'Online checkout is not active yet')
        oid, code = fields.get('order_id', [''])[0], fields.get('plan', [''])[0]
        if not re.fullmatch('[a-f0-9]{32}', oid) or code not in plans or fields.get('terms') != ['accepted']:
            raise HTTPException(400, 'Choose a plan and accept the agreed terms')
        now = int(clock())
        with engine.begin() as c:
            if c.dialect.name == 'postgresql':
                c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))'), {'id': row['subject']})
            order = c.execute(select(orders).where(orders.c.id == oid).with_for_update()).mappings().first()
            if order and (order['subject'] != row['subject'] or order['plan'] != code):
                raise HTTPException(409, 'Order identifier already used')
            if not order:
                recent = c.scalar(select(func.count()).select_from(orders).where(orders.c.subject == row['subject'], orders.c.created > now-86400))
                if recent >= 5:
                    raise HTTPException(429, 'Daily checkout limit reached')
                active = c.execute(select(orders.c.id).where(orders.c.subject == row['subject'], ((orders.c.state.in_(('active', 'trialing', 'past_due', 'unpaid', 'risk_review'))) | ((orders.c.state.in_(('creating', 'checkout_pending'))) & (orders.c.created > now-1800))))).first()
                if active:
                    raise HTTPException(409, 'Manage your existing subscription or contact TCL')
                c.execute(insert(orders).values(id=oid, subject=row['subject'], plan=code, state='creating', risk_hold=False, created=now, updated=now))
                order = c.execute(select(orders).where(orders.c.id == oid)).mappings().one()
                access._event(c, 'billing_order_created', row['subject'], oid, now)
        # Persist the order and fixed expiry before contacting Stripe: a network
        # timeout must not change parameters when retrying the idempotency key.
        with engine.begin() as c:
            order = c.execute(select(orders).where(orders.c.id == oid).with_for_update()).mappings().one()
            if order['created'] < now-1800:
                raise HTTPException(409, 'Checkout has expired; return to subscriptions')
            try:
                session = provider.checkout(order['checkout_id']) if order['checkout_id'] else provider.create(order, plans[code], config.origin)
            except Exception:
                raise HTTPException(503, 'Secure checkout unavailable; no payment has been confirmed') from None
            target = urlsplit(session['url'] or '')
            if target.scheme != 'https' or target.hostname != 'checkout.stripe.com' or target.username or target.password:
                raise HTTPException(503, 'Invalid checkout destination')
            if session.get('livemode') is not cfg.live or session.get('status') != 'open':
                raise HTTPException(409, 'Checkout is no longer available; check your billing status')
            c.execute(update(orders).where(orders.c.id == oid).values(checkout_id=session['id'], state='checkout_pending', updated=now))
        return RedirectResponse(session['url'], 303)

    @app.post('/customer/billing/portal')
    async def portal(request: Request):
        row = current(request)
        await protected_form(request, row)
        if not cfg.enabled:
            raise HTTPException(503, 'Billing management is not active yet')
        with engine.connect() as c:
            customer = c.scalar(select(orders.c.customer_id).where(orders.c.subject == row['subject'], orders.c.customer_id.is_not(None)).order_by(orders.c.created.desc()).limit(1))
        if not customer:
            raise HTTPException(404, 'No billing account found')
        try:
            result = provider.portal(customer, config.origin)
            url = result['url']
            target = urlsplit(url)
            if target.scheme != 'https' or target.hostname != 'billing.stripe.com' or target.username or target.password:
                raise ValueError('Invalid portal destination')
        except Exception:
            raise HTTPException(503, 'Billing management temporarily unavailable') from None
        return RedirectResponse(url, 303)

    @app.post('/api/webhooks/stripe')
    async def webhook(request: Request):
        if not cfg.enabled:
            raise HTTPException(503, 'Billing webhook is not active')
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 262144:
                raise HTTPException(413, 'Webhook too large')
        try:
            event = provider.verify(bytes(raw), request.headers.get('stripe-signature', ''))
        except Exception:
            raise HTTPException(400, 'Invalid Stripe signature') from None
        try:
            ledger.event(event)
        except ValueError:
            raise HTTPException(400, 'Invalid billing event') from None
        except Exception:
            raise HTTPException(503, 'Billing reconciliation pending; retry delivery') from None
        return JSONResponse({'received': True})

    @app.get('/admin/billing', response_class=HTMLResponse)
    def billing_admin(request: Request):
        row = current(request)
        try:
            with engine.begin() as c:
                access._actor(c, row['token_hash'], int(clock()))
                records = c.execute(select(orders).order_by(orders.c.updated.desc()).limit(100)).mappings().all() if cfg.enabled else []
        except Denied:
            raise HTTPException(403, 'Appointed administrator and recent MFA required') from None
        body = '<section class="card"><h2>Billing and licence follow-up</h2><p>Payment status does not issue a licence or approve access. Risk holds require investigation in Stripe. Installation licences remain signed separately.</p>'
        for r in records:
            body += '<p>Order ' + esc(r['id']) + ' · ' + esc(r['subject']) + ' · ' + esc(r['plan']) + ' · ' + esc(r['state']) + '</p>'
        return page('Commercial operations', body + '<p><a href="/admin/software-requests">Customer requests</a> · <a href="/admin/customers">Access approvals</a></p></section>')
    return ledger
