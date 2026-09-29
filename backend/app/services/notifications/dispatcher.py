from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import NotificationDelivery
from app.models.payer import Payer
from app.models.receipt import Receipt
from app.models.settlement import Settlement
from app.models.transaction import Transaction
from app.models.user import User
from app.services.notifications import config as ncfg
from app.services.notifications import email_module, sms_module, whatsapp_module


def _log_delivery(
    db: Session,
    *,
    tenant_id: Optional[str],
    channel: str,
    event_type: str,
    recipient: str,
    subject: Optional[str],
    body: str,
    status: str,
    error: Optional[str],
    entity_type: Optional[str],
    entity_id: Optional[str],
) -> NotificationDelivery:
    row = NotificationDelivery(
        tenant_id=tenant_id,
        channel=channel,
        event_type=event_type,
        recipient=recipient,
        subject=subject,
        body_preview=body[:2000],
        status=status,
        error_message=error,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(row)
    db.flush()
    from app.realtime.publisher import publish_notification_delivery

    publish_notification_delivery(row)
    return row


def _dispatch_channel(
    db: Session,
    *,
    tenant_id: Optional[str],
    channel: str,
    event_type: str,
    recipient: str,
    subject: str,
    body: str,
    entity_type: Optional[str],
    entity_id: Optional[str],
    send_fn,
) -> None:
    if not recipient:
        _log_delivery(
            db,
            tenant_id=tenant_id,
            channel=channel,
            event_type=event_type,
            recipient="",
            subject=subject,
            body=body,
            status="SKIPPED",
            error="No recipient",
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return
    if not ncfg.channel_enabled(db, tenant_id, channel):
        _log_delivery(
            db,
            tenant_id=tenant_id,
            channel=channel,
            event_type=event_type,
            recipient=recipient,
            subject=subject,
            body=body,
            status="SKIPPED",
            error=f"{channel} disabled",
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return
    if channel == "EMAIL":
        err = send_fn(recipient, subject, body)
    else:
        err = send_fn(recipient, body)
    _log_delivery(
        db,
        tenant_id=tenant_id,
        channel=channel,
        event_type=event_type,
        recipient=recipient,
        subject=subject,
        body=body,
        status="SENT" if err is None else "FAILED",
        error=err,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def notify_payment_settled(db: Session, txn: Transaction) -> None:
    payer = db.get(Payer, txn.payer_id)
    if not payer:
        return
    receipt = db.query(Receipt).filter(Receipt.transaction_id == txn.transaction_id).first()
    subject = f"EasyPay payment confirmed — {txn.transaction_reference}"
    body = (
        f"Hello {payer.full_name},\n\n"
        f"Your payment of {txn.total_amount} {txn.currency} was settled successfully.\n"
        f"Reference: {txn.transaction_reference}\n"
    )
    if receipt:
        body += f"Receipt: {receipt.receipt_number}\n"
    tenant_id = txn.transaction_tenant_id
    entity_id = txn.transaction_id
    _dispatch_channel(
        db,
        tenant_id=tenant_id,
        channel="EMAIL",
        event_type="PAYMENT_SETTLED",
        recipient=payer.email or "",
        subject=subject,
        body=body,
        entity_type="transaction",
        entity_id=entity_id,
        send_fn=email_module.send_email,
    )
    sms_body = f"EasyPay: payment {txn.transaction_reference} settled. Total {txn.total_amount} {txn.currency}."
    _dispatch_channel(
        db,
        tenant_id=tenant_id,
        channel="SMS",
        event_type="PAYMENT_SETTLED",
        recipient=payer.phone_number or "",
        subject=subject,
        body=sms_body,
        entity_type="transaction",
        entity_id=entity_id,
        send_fn=sms_module.send_sms,
    )
    _dispatch_channel(
        db,
        tenant_id=tenant_id,
        channel="WHATSAPP",
        event_type="PAYMENT_SETTLED",
        recipient=payer.phone_number or "",
        subject=subject,
        body=sms_body,
        entity_type="transaction",
        entity_id=entity_id,
        send_fn=whatsapp_module.send_whatsapp,
    )


def notify_zone_change_decision(db: Session, payer: Payer, approved: bool, notes: Optional[str] = None) -> None:
    subject = "EasyPay operating area update"
    body = (
        f"Hello {payer.full_name},\n\n"
        f"Your operating area change request was {'approved' if approved else 'rejected'}.\n"
    )
    if notes:
        body += f"Notes: {notes}\n"
    tenant_id = payer.tenant_id
    _dispatch_channel(
        db,
        tenant_id=tenant_id,
        channel="EMAIL",
        event_type="ZONE_CHANGE_DECISION",
        recipient=payer.email or "",
        subject=subject,
        body=body,
        entity_type="payer",
        entity_id=payer.payer_id,
        send_fn=email_module.send_email,
    )
    short = f"EasyPay: zone change {'approved' if approved else 'rejected'}."
    _dispatch_channel(
        db,
        tenant_id=tenant_id,
        channel="SMS",
        event_type="ZONE_CHANGE_DECISION",
        recipient=payer.phone_number or "",
        subject=subject,
        body=short,
        entity_type="payer",
        entity_id=payer.payer_id,
        send_fn=sms_module.send_sms,
    )
    _dispatch_channel(
        db,
        tenant_id=tenant_id,
        channel="WHATSAPP",
        event_type="ZONE_CHANGE_DECISION",
        recipient=payer.phone_number or "",
        subject=subject,
        body=short,
        entity_type="payer",
        entity_id=payer.payer_id,
        send_fn=whatsapp_module.send_whatsapp,
    )


def notify_settlement_approved(db: Session, settlement: Settlement, approver_id: str) -> None:
    approver = db.get(User, approver_id)
    tenant_users = (
        db.query(User)
        .filter(User.tenant_id == settlement.tenant_id, User.user_type.in_(["STAFF", "PLATFORM_ADMIN"]), User.is_active.is_(True))
        .all()
    )
    recipients = {u.email for u in tenant_users if u.email}
    if approver and approver.email:
        recipients.add(approver.email)
    subject = f"Settlement {settlement.settlement_reference} approved"
    body = (
        f"Settlement {settlement.settlement_reference} for period "
        f"{settlement.period_start.date()} – {settlement.period_end.date()} was approved.\n"
        f"Net amount: {settlement.net_amount} {settlement.currency}\n"
    )
    for email in recipients:
        _dispatch_channel(
            db,
            tenant_id=settlement.tenant_id,
            channel="EMAIL",
            event_type="SETTLEMENT_APPROVED",
            recipient=email,
            subject=subject,
            body=body,
            entity_type="settlement",
            entity_id=settlement.settlement_id,
            send_fn=email_module.send_email,
        )
