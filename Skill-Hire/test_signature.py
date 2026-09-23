"""
Proves the HMAC signature logic is correct WITHOUT needing network access
or real Razorpay keys — we sign test payloads with a fake secret ourselves,
exactly like Razorpay's server does, then check our verifier accepts the
valid one and rejects a tampered one.

Run:  python test_signature.py
"""
import hashlib
import hmac
import os

os.environ["RAZORPAY_KEY_SECRET"] = "test_secret_abc123"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test_webhook_secret_xyz789"

import payments  # noqa: E402  (import after env vars are set, since payments reads them at import time)


def test_valid_checkout_signature():
    order_id, payment_id = "order_ABC123", "pay_XYZ789"
    body = f"{order_id}|{payment_id}"
    real_signature = hmac.new(
        os.environ["RAZORPAY_KEY_SECRET"].encode(), body.encode(), hashlib.sha256
    ).hexdigest()

    assert payments.verify_checkout_signature(order_id, payment_id, real_signature) is True
    print("PASS: valid checkout signature accepted")


def test_tampered_checkout_signature_rejected():
    order_id, payment_id = "order_ABC123", "pay_XYZ789"
    fake_signature = "0" * 64  # not a real HMAC output
    result = payments.verify_checkout_signature(order_id, payment_id, fake_signature)
    assert result is False
    print("PASS: tampered checkout signature correctly rejected")


def test_valid_webhook_signature():
    raw_body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_XYZ789"}}}}'
    real_signature = hmac.new(
        os.environ["RAZORPAY_WEBHOOK_SECRET"].encode(), raw_body, hashlib.sha256
    ).hexdigest()

    assert payments.verify_webhook_signature(raw_body, real_signature) is True
    print("PASS: valid webhook signature accepted")


def test_tampered_webhook_body_rejected():
    raw_body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_XYZ789"}}}}'
    real_signature = hmac.new(
        os.environ["RAZORPAY_WEBHOOK_SECRET"].encode(), raw_body, hashlib.sha256
    ).hexdigest()

    tampered_body = raw_body.replace(b"pay_XYZ789", b"pay_HACKED1")
    result = payments.verify_webhook_signature(tampered_body, real_signature)
    assert result is False
    print("PASS: tampered webhook body correctly rejected")


def test_missing_config_raises():
    os.environ.pop("RAZORPAY_KEY_SECRET", None)
    import importlib
    importlib.reload(payments)
    try:
        payments.verify_checkout_signature("order_1", "pay_1", "whatever")
        print("FAIL: should have raised RazorpayConfigError")
    except payments.RazorpayConfigError:
        print("PASS: missing key secret correctly raises RazorpayConfigError")
    finally:
        os.environ["RAZORPAY_KEY_SECRET"] = "test_secret_abc123"
        importlib.reload(payments)


if __name__ == "__main__":
    test_valid_checkout_signature()
    test_tampered_checkout_signature_rejected()
    test_valid_webhook_signature()
    test_tampered_webhook_body_rejected()
    test_missing_config_raises()
    print("\nAll signature checks behave correctly.")
