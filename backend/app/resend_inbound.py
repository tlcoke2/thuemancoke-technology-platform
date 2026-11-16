"""Forward authenticated Resend events for the TCL enterprise enquiries alias."""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import time
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request as HttpRequest, build_opener
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from .settings import get_settings


router = APIRouter()
logger = logging.getLogger("thueman-coke-api")
ALIAS = "enquiries@thuemancokelimited.com"
API_URL = "https://api.resend.com"
MAX_WEBHOOK_BYTES = 256 * 1024
MAX_RAW_BYTES = 24 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def valid_signature(headers, body, secret, now):
    try:
        message_id = headers["svix-id"]
        timestamp = headers["svix-timestamp"]
        signatures = headers["svix-signature"].split()
        if not secret.startswith("whsec_") or abs(now - int(timestamp)) > 300:
            return False
        key = base64.b64decode(secret[6:], validate=True)
        if not key:
            return False
        signed = f"{message_id}.{timestamp}.".encode() + body
        expected = base64.b64encode(hmac.digest(key, signed, hashlib.sha256))
        return any(
            candidate.startswith("v1,") and hmac.compare_digest(candidate[3:].encode(), expected)
            for candidate in signatures
        )
    except (KeyError, ValueError, binascii.Error):
        return False


def includes_alias(recipients):
    return isinstance(recipients, list) and any(
        isinstance(address, str) and parseaddr(address)[1].casefold() == ALIAS
        for address in recipients
    )


def fetch(request, limit, *, stage):
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Resend response exceeds the forwarding limit")
    except HTTPError as error:
        logger.warning("Inbound forwarding upstream failure stage=%s status=%d", stage, error.code)
        raise
    except (OSError, ValueError) as error:
        logger.warning("Inbound forwarding upstream failure stage=%s kind=%s", stage, type(error).__name__)
        raise
    return data


def forward_message(email_id, api_key, sender, destination):
    auth = {"Authorization": f"Bearer {api_key}"}
    received = json.loads(fetch(
        HttpRequest(f"{API_URL}/emails/receiving/{email_id}", headers=auth),
        MAX_WEBHOOK_BYTES,
        stage="receive_metadata",
    ))
    if not includes_alias(received.get("to")):
        return
    link = received["raw"]["download_url"]
    parsed_link = urlsplit(link)
    if parsed_link.scheme != "https" or not parsed_link.hostname or parsed_link.username or parsed_link.password:
        raise ValueError("Invalid Resend raw email download location")
    raw = fetch(HttpRequest(link), MAX_RAW_BYTES, stage="download_original")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    body = message.get_body(preferencelist=("plain",))
    original_sender = parseaddr(received.get("from") or "")[1]
    if original_sender.casefold() in {ALIAS, parseaddr(sender)[1].casefold()}:
        return
    preview = body.get_content()[:12000] if body else ""
    subject = " ".join((received.get("subject") or "(no subject)").splitlines())[:240]
    payload = {
        "from": sender,
        "to": [destination],
        "subject": f"Enterprise enquiry: {subject}",
        "text": f"Original sender: {original_sender}\n\n{preview}\n\nThe original message is attached.",
        "attachments": [{
            "filename": "original-enquiry.eml",
            "content": base64.b64encode(raw).decode("ascii"),
        }],
    }
    if original_sender:
        payload["reply_to"] = original_sender
    fetch(HttpRequest(
        f"{API_URL}/emails",
        data=json.dumps(payload).encode(),
        headers={
            **auth,
            "Content-Type": "application/json",
            "Idempotency-Key": f"tcl-enterprise-forward/{email_id}",
        },
        method="POST",
    ), MAX_WEBHOOK_BYTES, stage="send_forward")


@router.post("/api/webhooks/resend/inbound", include_in_schema=False)
async def resend_inbound(request: Request):
    secret = os.getenv("RESEND_INBOUND_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, "Forwarding is not configured")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_WEBHOOK_BYTES:
            raise HTTPException(413, "Webhook payload too large")
        body.extend(chunk)
    if not valid_signature(request.headers, bytes(body), secret, time.time()):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        event = json.loads(body)
        if event["type"] != "email.received" or not includes_alias(event["data"].get("to")):
            return Response(status_code=200)
        email_id = str(UUID(event["data"]["email_id"]))
    except (AttributeError, KeyError, TypeError, ValueError):
        raise HTTPException(400, "Invalid webhook payload") from None
    api_key = os.getenv("RESEND_INBOUND_API_KEY", "")
    settings = get_settings()
    if not api_key or not settings.from_email or not settings.contact_to_email:
        raise HTTPException(503, "Forwarding is not configured")
    try:
        await run_in_threadpool(
            forward_message, email_id, api_key, settings.from_email, settings.contact_to_email,
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        if not isinstance(error, OSError):
            logger.warning("Inbound forwarding processing failure kind=%s", type(error).__name__)
        raise HTTPException(502, "Resend forwarding failed") from None
    return Response(status_code=200)
