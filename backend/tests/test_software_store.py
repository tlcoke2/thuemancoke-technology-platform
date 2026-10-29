"""Synthetic-only verification of TCL software-store registration and privacy gates."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TMP = Path(tempfile.mkdtemp(prefix="tcl-store-test-"))
os.environ["DATABASE_URL"] = "sqlite:///" + str(TMP / "isolated.sqlite")
os.environ["APP_ENV"] = "development"
os.environ["SOFTWARE_LEADS_ENABLED"] = "false"

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import SalesLead
from app.software_store import (
    SoftwareInterest, SoftwareStoreSettings, get_store_settings,
)

FORM = {
    "product_id": "tec-epr-clinic-edition",
    "request_type": "trial",
    "full_name": "Test Clinic Administrator",
    "business_email": "clinic@example.com",
    "organisation": "Synthetic Clinic Limited",
    "country": "Jamaica",
    "contact_consent": True,
    "marketing_opt_in": False,
    "website": "",
    "turnstile_token": "",
}


class SoftwareStoreTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            db.query(SoftwareInterest).delete()
            db.query(SalesLead).filter(SalesLead.source == "TCL software store").delete()
            db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def settings(self, enabled=True, production=False):
        config = SoftwareStoreSettings(
            app_env="production" if production else "development",
            software_leads_enabled=enabled,
            software_turnstile_site_key="site-test" if production else "",
            software_turnstile_secret_key="secret-test" if production else "",
        )
        app.dependency_overrides[get_store_settings] = lambda: config

    def counts(self):
        with SessionLocal() as db:
            return (
                db.query(SoftwareInterest).count(),
                db.query(SalesLead).filter(SalesLead.source == "TCL software store").count(),
            )

    def test_catalog_has_no_public_download_link(self):
        response = self.client.get("/api/software/catalog")
        self.assertEqual(response.status_code, 200)
        result = response.json()["products"][0]
        self.assertEqual(result["id"], FORM["product_id"])
        self.assertFalse(result["downloadAvailable"])
        self.assertNotIn("downloadUrl", result)

    def test_production_registration_fails_closed_until_enabled(self):
        self.settings(enabled=False, production=True)
        config = self.client.get("/api/software/registration-config").json()
        self.assertFalse(config["acceptingRequests"])
        response = self.client.post("/api/software/interest", json=FORM)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.counts(), (0, 0))

    def test_production_requires_turnstile_secret_and_valid_response(self):
        self.settings(production=True)
        with patch("app.software_store.verify_turnstile", return_value=False) as verification:
            response = self.client.post("/api/software/interest", json=FORM)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.counts(), (0, 0))
            verification.assert_called_once()

    def test_acceptance_creates_one_request_and_one_crm_lead_atomically(self):
        self.settings()
        response = self.client.post("/api/software/interest", json=FORM)
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json()["accepted"])
        self.assertIn("No trial or licence has been issued", response.json()["message"])
        self.assertEqual(self.counts(), (1, 1))
        with SessionLocal() as db:
            row = db.query(SoftwareInterest).one()
            lead = db.query(SalesLead).filter(SalesLead.source == "TCL software store").one()
            self.assertFalse(row.marketing_opt_in)
            self.assertEqual(row.privacy_notice_version, "2026-10-29-software-interest-v1")
            self.assertEqual(row.business_email, FORM["business_email"])
            self.assertIn(row.id, lead.notes)
            self.assertEqual(lead.currency, "JMD")

    def test_marketing_requires_separate_opt_in(self):
        self.settings()
        form = dict(FORM, marketing_opt_in=True)
        self.assertEqual(self.client.post("/api/software/interest", json=form).status_code, 202)
        with SessionLocal() as db:
            self.assertTrue(db.query(SoftwareInterest).one().marketing_opt_in)

    def test_required_contact_consent_and_unknown_product_are_rejected(self):
        self.settings()
        for form in [dict(FORM, contact_consent=False), dict(FORM, product_id="another-product")]:
            self.assertEqual(self.client.post("/api/software/interest", json=form).status_code, 422)
        self.assertEqual(self.counts(), (0, 0))

    def test_honeypot_drops_all_data_and_prevents_crm_creation(self):
        self.settings()
        response = self.client.post("/api/software/interest", json=dict(FORM, website="https://bot.invalid"))
        self.assertEqual(response.status_code, 202)
        self.assertIsNone(response.json()["reference"])
        self.assertEqual(self.counts(), (0, 0))

    def test_production_allows_only_after_verified_captcha(self):
        self.settings(production=True)
        with patch("app.software_store.verify_turnstile", return_value=True):
            response = self.client.post("/api/software/interest", json=dict(FORM, turnstile_token="synthetic"))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.counts(), (1, 1))


if __name__ == "__main__":
    unittest.main()
