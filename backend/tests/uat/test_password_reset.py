"""UAT for forgotten-password OTP flow (email / SMS / WhatsApp)."""

import re

from app.db.session import SessionLocal
from app.models.notification import NotificationDelivery
from app.models.password_reset import PasswordResetChallenge
from app.models.user import User
from app.services.password_reset import peek_latest_otp_for_tests


def _clear_challenges_for(*identifiers: str) -> None:
    db = SessionLocal()
    try:
        user_ids = []
        for ident in identifiers:
            user = (
                db.query(User)
                .filter((User.username == ident) | (User.email == ident) | (User.phone_number == ident))
                .first()
            )
            if user:
                user_ids.append(user.user_id)
        if user_ids:
            db.query(PasswordResetChallenge).filter(PasswordResetChallenge.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            db.commit()
    finally:
        db.close()


def _otp_from_challenge(challenge_id: str) -> str:
    db = SessionLocal()
    try:
        otp = peek_latest_otp_for_tests(db, challenge_id)
        assert otp and re.fullmatch(r"\d{6}", otp), f"OTP not found in delivery log for {challenge_id}"
        return otp
    finally:
        db.close()


def test_uat_password_reset_channels_public(client):
    r = client.get("/api/v1/auth/password-reset/channels")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] is True
    assert body["whatsapp"] is True
    assert body["sms"] is False  # master switch off by default
    assert body["otp_length"] == 6


def test_uat_forgot_password_unknown_user_no_leak(client):
    r = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "definitely-not-a-user-xyz", "channel": "EMAIL"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["challenge_id"] is None
    assert "one-time code" in body["message"].lower() or "code was sent" in body["message"].lower()


def test_uat_password_reset_email_flow_for_payer(client):
    _clear_challenges_for("abctrading", "abc@traders.local", "670000001")
    # Request OTP via email
    r = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "abctrading", "channel": "EMAIL"},
    )
    assert r.status_code == 200, r.text
    challenged = r.json()
    assert challenged["challenge_id"]
    assert challenged["channel"] == "EMAIL"
    assert challenged["destination_hint"]
    assert "@" in challenged["destination_hint"]
    assert challenged.get("demo_otp") and len(challenged["demo_otp"]) == 6

    otp = challenged["demo_otp"]
    assert otp == _otp_from_challenge(challenged["challenge_id"])

    # Wrong OTP rejected
    bad = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenged["challenge_id"], "otp": "000000"},
    )
    assert bad.status_code == 400

    # Correct OTP
    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenged["challenge_id"], "otp": otp},
    )
    assert verified.status_code == 200, verified.text
    reset_token = verified.json()["reset_token"]
    assert reset_token

    new_password = "payerReset99"
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": new_password,
            "new_password_confirm": new_password,
        },
    )
    assert reset.status_code == 200, reset.text

    # Old password fails, new works
    old = client.post("/api/v1/auth/login", json={"username": "abctrading", "password": "payer123"})
    assert old.status_code == 401
    ok = client.post("/api/v1/auth/login", json={"username": "abctrading", "password": new_password})
    assert ok.status_code == 200, ok.text

    # Restore seed password so other UAT suites stay green
    r2 = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "abc@traders.local", "channel": "EMAIL"},
    )
    assert r2.status_code == 200, r2.text
    cid = r2.json()["challenge_id"]
    assert cid
    otp2 = _otp_from_challenge(cid)
    tok = client.post("/api/v1/auth/verify-otp", json={"challenge_id": cid, "otp": otp2}).json()["reset_token"]
    restored = client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": tok,
            "new_password": "payer123",
            "new_password_confirm": "payer123",
        },
    )
    assert restored.status_code == 200, restored.text
    assert client.post("/api/v1/auth/login", json={"username": "abctrading", "password": "payer123"}).status_code == 200


def test_uat_password_reset_whatsapp_channel(client):
    _clear_challenges_for("abctrading", "670000001")
    r = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "670000001", "channel": "WHATSAPP"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["challenge_id"]
    assert body["channel"] == "WHATSAPP"
    assert body["destination_hint"]

    db = SessionLocal()
    try:
        delivery = (
            db.query(NotificationDelivery)
            .filter(
                NotificationDelivery.entity_id == body["challenge_id"],
                NotificationDelivery.channel == "WHATSAPP",
                NotificationDelivery.event_type == "PASSWORD_RESET_OTP",
            )
            .first()
        )
        assert delivery is not None
        assert delivery.status in ("SENT", "SKIPPED", "FAILED")
        # Without WhatsApp API URL configured, provider returns success (None) → SENT
        assert delivery.status == "SENT"
    finally:
        db.close()


def test_uat_password_reset_sms_disabled_by_default(client):
    r = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "abctrading", "channel": "SMS"},
    )
    assert r.status_code == 400, r.text
    assert "unavailable" in r.json()["detail"].lower()


def test_uat_password_reset_cooldown_returns_existing_challenge(client):
    _clear_challenges_for("abctrading")
    first = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "abctrading", "channel": "EMAIL"},
    )
    assert first.status_code == 200, first.text
    cid = first.json()["challenge_id"]
    assert cid
    assert first.json().get("demo_otp")

    second = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "abctrading", "channel": "EMAIL"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["challenge_id"] == cid
    assert "already sent" in second.json()["message"].lower()


def test_uat_password_reset_staff_user_email(client):
    _clear_challenges_for("kumba1_admin")
    r = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "kumba1_admin", "channel": "EMAIL"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Staff seed users have council emails
    if body["challenge_id"]:
        otp = _otp_from_challenge(body["challenge_id"])
        verified = client.post(
            "/api/v1/auth/verify-otp",
            json={"challenge_id": body["challenge_id"], "otp": otp},
        )
        assert verified.status_code == 200, verified.text
        # Do not change staff password — leave after OTP verify only
