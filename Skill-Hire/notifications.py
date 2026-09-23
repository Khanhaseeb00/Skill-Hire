"""
SMS notifications — uses Twilio's REST API directly via `requests` (no SDK
dependency, same lightweight pattern as payments.py).

Needs network + real credentials to actually send, so it can't be exercised
live in an offline sandbox — but every call is wrapped in try/except at the
call site, so a missing config or a failed send NEVER breaks the booking
flow itself. Notifications are a side effect, not a dependency.

For India-only use, MSG91 or a local SMS gateway is usually cheaper than
Twilio — swap the URL/auth in send_sms() for theirs; the rest of this file
(and every call site) stays the same.
"""
import os
import requests

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

API_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class NotificationConfigError(Exception):
    pass


def send_sms(to_phone, body):
    """
    Sends one SMS. Raises on failure — callers should wrap this in
    try/except and log rather than let it break the request they're
    handling (see app.py's notify() helper).
    """
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        raise NotificationConfigError(
            "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER not set. "
            "Get free trial credentials at twilio.com and add them to .env."
        )
    # Indian numbers need a country code for Twilio; add +91 if missing.
    to = to_phone if to_phone.startswith("+") else "+91" + to_phone

    resp = requests.post(
        API_URL.format(sid=TWILIO_ACCOUNT_SID),
        data={"From": TWILIO_FROM_NUMBER, "To": to, "Body": body},
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
