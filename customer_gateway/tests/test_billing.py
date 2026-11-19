import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import select, insert, func, create_engine, text
from customer_gateway.tests.test_customer_intake import IntakeTests
from customer_gateway.app import SESSION_COOKIE
from customer_gateway.billing import (BillingConfig, StripeBilling, Ledger, metadata,
    orders, receipts, register, subscription_of, EVENTS)
from customer_gateway.migrate_billing import migrate, BASE

class Provider:
    def __init__(self):
        self.sessions = {}
        self.sub = {'id':'sub_synthetic', 'customer':'cus_synthetic', 'status':'active',
                    'livemode':False, 'latest_invoice':{'status':'paid'}}
        self.created = 0
        self.fail = False
        self.portal_customer = None
    def create(self, order, plan, origin):
        self.created += 1
        if self.fail: raise RuntimeError('provider unavailable')
        result = {'id':'cs_test_synthetic', 'url':'https://checkout.stripe.com/test',
                  'client_reference_id':order['id'], 'livemode':False,
                  'mode':'subscription', 'status':'open', 'subscription':None}
        self.sessions[result['id']] = result
        return result
    def checkout(self, sid): return self.sessions[sid]
    def subscription(self, sid): return self.sub
    def checkout_for_subscription(self, sid): return list(self.sessions.values())
    def risk_subscriptions(self, obj): return ['sub_synthetic']
    def verify(self, raw, signature):
        import stripe
        return stripe.Webhook.construct_event(raw, signature, 'whsec_synthetic', tolerance=300).to_dict()
    def portal(self, customer, origin):
        self.portal_customer = customer
        return {'url':'https://billing.stripe.com/test'}

class BillingTests(IntakeTests):
    def setUp(self):
        super().setUp()
        metadata.create_all(self.engine)
        self.provider = Provider()
        self.cfg = BillingConfig(True, 'rk_test_synthetic', 'whsec_synthetic', False, 'acct_synthetic', True)
        # Register on a small isolated app using the production authentication and
        # protected-form functions captured from the app's existing intake routes.
        app = self.client.app
        intake_endpoint = next(r.endpoint for r in app.routes if getattr(r,'path','') == '/customer/requests' and 'POST' in getattr(r,'methods',[]))
        captured = dict(zip(intake_endpoint.__code__.co_freevars, [c.cell_contents for c in intake_endpoint.__closure__]))
        self.app = FastAPI()
        self.ledger = register(self.app, type('Cfg',(),{'origin':'https://customers.example.com'})(), self.engine,
            captured['current'], captured['protected_form'], lambda:self.now, captured['access'], self.cfg, self.provider)
        self.billing = TestClient(self.app, base_url='https://customers.example.com')
        self.billing.cookies.set(SESSION_COOKIE,'browser')
    def tearDown(self):
        metadata.drop_all(self.engine)
        super().tearDown()
    def checkout(self, **changes):
        fields={'csrf':'synthetic','order_id':'a'*32,'plan':'clinic_essentials','terms':'accepted'}
        fields.update(changes)
        return self.billing.post('/customer/billing/checkout', data=fields,
            headers={'Origin':'https://customers.example.com'}, follow_redirects=False)
    def event(self, kind='checkout.session.completed', eid='evt_synthetic', **extra):
        self.provider.sessions['cs_test_synthetic']['status']='complete'
        self.provider.sessions['cs_test_synthetic']['subscription']='sub_synthetic'
        obj={'id':'cs_test_synthetic'}
        if kind.startswith('customer.subscription.'): obj={'id':'sub_synthetic'}
        if kind.startswith('invoice.'): obj={'id':'in_synthetic','parent':{'type':'subscription_details','subscription_details':{'subscription':'sub_synthetic'}}}
        event={'id':eid,'type':kind,'livemode':False,'data':{'object':obj}}
        event.update(extra)
        return event
    def state(self):
        with self.engine.connect() as c: return c.execute(select(orders)).mappings().first()
    def post_event(self, event, timestamp=None, signature=None):
        raw=json.dumps(event).encode()
        timestamp=timestamp or int(time.time())
        mac=hmac.new(b'whsec_synthetic', str(timestamp).encode()+b'.'+raw, hashlib.sha256).hexdigest()
        return self.billing.post('/api/webhooks/stripe',content=raw,headers={'stripe-signature':signature or f't={timestamp},v1={mac}'})
    def test_public_payment_options_and_authenticated_link_requests(self):
        self.billing.cookies.clear()
        r=self.billing.get('/payments')
        self.assertEqual(r.status_code,200)
        for plan in ('Clinic Essentials','Professional','Enterprise'):
            self.assertIn(plan,r.text)
        self.assertIn('Request a payment link',r.text)
        self.assertNotIn('name="card',r.text)
        self.assertEqual(self.billing.get('/customer/billing').status_code,401)

    def test_disabled_billing_still_shows_payment_request_gui(self):
        r=self.client.get('/payments')
        self.assertEqual(r.status_code,200)
        self.assertIn('Card checkout is not available yet',r.text)
        self.assertIn('paylink_professional',r.text)
        self.assertNotIn('action="/customer/billing/checkout"',r.text)

    def test_checkout_auth_csrf_unknown_plan_and_price_injection(self):
        self.assertEqual(self.checkout(csrf='wrong').status_code,403)
        self.assertEqual(self.checkout(plan='price_attacker').status_code,400)
        self.assertEqual(self.checkout(terms='no').status_code,400)
        self.billing.cookies.clear()
        self.assertEqual(self.checkout().status_code,401)
        self.assertEqual(self.provider.created,0)
    def test_checkout_is_idempotent_and_success_page_does_not_fulfil(self):
        self.assertEqual(self.checkout().status_code,303)
        self.assertEqual(self.checkout().status_code,303)
        self.assertEqual(self.provider.created,1)
        self.assertEqual(self.state()['state'],'checkout_pending')
        r=self.billing.get('/customer/billing?checkout=returned')
        self.assertIn('text/html',r.headers['content-type'])
        self.assertEqual(self.state()['state'],'checkout_pending')
        self.assertEqual(self.checkout(order_id='b'*32).status_code,409)
    def test_network_retry_preserves_order_and_fixed_parameters(self):
        self.provider.fail=True
        self.assertEqual(self.checkout().status_code,503)
        original=self.state()['created']
        self.now+=30; self.provider.fail=False
        self.assertEqual(self.checkout().status_code,303)
        self.assertEqual(self.state()['created'],original)
    def test_signed_duplicate_event_reconciles_once_and_never_grants_licence(self):
        self.checkout()
        event=self.event()
        self.assertEqual(self.post_event(event).status_code,200)
        self.assertEqual(self.post_event(event).status_code,200)
        self.assertEqual(self.state()['state'],'active')
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(receipts)),1)
            from customer_gateway.entitlements import grants
            self.assertEqual(c.scalar(select(func.count()).select_from(grants)),0)
    def test_invalid_old_signature_wrong_mode_and_oversized_denied(self):
        self.checkout(); e=self.event()
        self.assertEqual(self.post_event(e,signature='invalid').status_code,400)
        self.assertEqual(self.post_event(e,timestamp=int(time.time())-600).status_code,400)
        e['livemode']=True
        self.assertEqual(self.post_event(e).status_code,400)
        self.assertEqual(self.billing.post('/api/webhooks/stripe',content=b'x'*262145).status_code,413)
        self.assertEqual(self.state()['state'],'checkout_pending')
    def test_out_of_order_invoice_finds_first_class_checkout(self):
        self.checkout()
        self.assertEqual(self.post_event(self.event('invoice.paid')).status_code,200)
        self.assertEqual(self.state()['subscription_id'],'sub_synthetic')
    def test_unpaid_checkout_never_marked_paid(self):
        self.checkout(); self.provider.sub['latest_invoice']={'status':'open'}
        self.assertEqual(self.post_event(self.event()).status_code,200)
        self.assertEqual(self.state()['state'],'pending_payment')
    def test_risk_hold_is_sticky_across_later_renewal_and_blocks_download(self):
        self.checkout(); self.post_event(self.event())
        risk={'id':'evt_risk','type':'charge.refunded','livemode':False,'data':{'object':{'id':'ch_synthetic'}}}
        self.assertEqual(self.post_event(risk).status_code,200)
        self.assertEqual(self.post_event(self.event('invoice.paid','evt_later')).status_code,200)
        self.assertEqual(self.state()['state'],'risk_review')
        with self.assertRaises(HTTPException):self.ledger.require_download_clear('user_customer')
        self.ledger.require_download_clear('user_other')
    def test_cancel_and_failure_reconcile_current_provider_state(self):
        self.checkout()
        self.provider.sub['status']='past_due'
        self.assertEqual(self.post_event(self.event('invoice.payment_failed')).status_code,200)
        self.assertEqual(self.state()['state'],'past_due')
        self.provider.sub['status']='canceled'
        self.assertEqual(self.post_event(self.event('customer.subscription.deleted','evt_cancel')).status_code,200)
        self.assertEqual(self.state()['state'],'canceled')
    def test_provider_failure_is_retryable_without_event_receipt(self):
        self.checkout(); event=self.event()
        with patch.object(self.provider,'subscription',side_effect=RuntimeError('temporary')):
            self.assertEqual(self.post_event(event).status_code,503)
        with self.engine.connect() as c:self.assertEqual(c.scalar(select(func.count()).select_from(receipts)),0)
        self.assertEqual(self.post_event(event).status_code,200)
    def test_ownership_mismatch_and_cross_customer_portal_denied(self):
        self.checkout(); event=self.event()
        self.provider.sessions['cs_test_synthetic']['client_reference_id']='b'*32
        self.assertEqual(self.post_event(event).status_code,400)
        self.assertEqual(self.billing.post('/customer/billing/portal',data={'csrf':'synthetic'},headers={'Origin':'https://customers.example.com'}).status_code,404)
    def test_unrelated_account_checkout_acknowledged(self):
        self.checkout(); e=self.event(); self.provider.sessions['cs_test_synthetic']['id']='cs_other'
        self.provider.sessions['cs_other']=self.provider.sessions.pop('cs_test_synthetic')
        self.provider.sessions['cs_other']['client_reference_id']='b'*32
        e['data']['object']['id']='cs_other'
        self.assertEqual(self.post_event(e).status_code,200)
        self.assertEqual(self.state()['state'],'checkout_pending')
    def test_portal_uses_bound_customer_only_and_admin_requires_mfa(self):
        self.checkout(); self.post_event(self.event())
        r=self.billing.post('/customer/billing/portal',data={'csrf':'synthetic','customer':'cus_attacker'},headers={'Origin':'https://customers.example.com'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        self.assertEqual(self.provider.portal_customer,'cus_synthetic')
        self.assertEqual(self.billing.get('/admin/billing').status_code,403)

class BillingConfigurationTests(unittest.TestCase):
    def test_enabled_requires_restricted_key_webhook_and_acceptance(self):
        with patch.dict(os.environ,{'GATEWAY_BILLING_ENABLED':'true'},clear=True):
            with self.assertRaises(RuntimeError):BillingConfig.environment()
        with patch.dict(os.environ,{},clear=True):self.assertFalse(BillingConfig.environment().enabled)
    def test_migration_is_additive_repeatable_and_refuses_unrelated_table(self):
        engine=create_engine('sqlite://')
        with engine.begin() as c:
            for m in BASE:m.create_all(c)
            migrate(c); migrate(c)
            self.assertEqual(c.scalar(select(func.count()).select_from(orders)),0)
            c.execute(text('CREATE TABLE clinical_records (id INTEGER)'))
            with self.assertRaises(RuntimeError):migrate(c)
        engine.dispose()
    def test_risk_graph_uses_invoice_payments_and_parent_subscription(self):
        adapter=object.__new__(StripeBilling);adapter.client=MagicMock()
        adapter.client.v1.invoice_payments.list.return_value.auto_paging_iter.return_value=iter([type('P',(),{'invoice':'in_one'})(),type('P',(),{'invoice':'in_two'})()])
        adapter.client.v1.invoices.retrieve.return_value.to_dict.side_effect=[{'parent':{'type':'subscription_details','subscription_details':{'subscription':'sub_one'}}},{'parent':{'type':'subscription_details','subscription_details':{'subscription':'sub_two'}}}]
        self.assertEqual(adapter.risk_subscriptions({'payment_intent':'pi_one'}),['sub_one','sub_two'])
        args=adapter.client.v1.invoice_payments.list.call_args.args[0]
        self.assertEqual(args['payment'],{'type':'payment_intent','payment_intent':'pi_one'})
    def test_live_checkout_requires_charges_enabled_on_selected_account(self):
        adapter=object.__new__(StripeBilling); adapter.client=MagicMock()
        adapter.cfg=BillingConfig(live=True,account='acct_selected')
        account=adapter.client.v1.accounts.retrieve_current.return_value
        account.id='acct_selected';account.charges_enabled=False
        with self.assertRaises(ValueError):adapter.check_account()
        account.charges_enabled=True
        adapter.check_account()
        account.id='acct_other'
        with self.assertRaises(ValueError):adapter.check_account()

    def test_sdk_checkout_has_tax_idempotency_dynamic_methods_and_fixed_return(self):
        adapter=object.__new__(StripeBilling);adapter.client=MagicMock();adapter.cfg=BillingConfig(live=False)
        adapter.check_account=MagicMock()
        price=adapter.client.v1.prices.retrieve.return_value
        price.id='price_synthetic';price.unit_amount=2500000;price.currency='jmd';price.tax_behavior='exclusive';price.active=True;price.livemode=False;price.product='prod_synthetic';price.recurring.interval='month'
        adapter.create({'id':'a'*32,'created':10000},{'stripeMonthlyPriceId':price.id,'monthlyMinor':2500000,'stripeProductId':'prod_synthetic'},'https://customers.example.com')
        args=adapter.client.v1.checkout.sessions.create.call_args.args[0]
        self.assertTrue(args['automatic_tax']['enabled']);self.assertTrue(args['tax_id_collection']['enabled'])
        self.assertNotIn('payment_method_types',args)
        self.assertEqual(args['expires_at'],11800)
        self.assertRegex(args['integration_identifier'],r'^tcl_gateway_[a-z]{8}$')
        self.assertEqual(adapter.client.v1.checkout.sessions.create.call_args.kwargs['options']['idempotency_key'],'tcl-checkout-'+'a'*32)
