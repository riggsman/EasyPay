from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.notification import NotificationDelivery
from app.models.payer import Payer
from app.models.settlement import Settlement
from app.models.transaction import Transaction
from app.realtime import schemas as evt
from app.realtime.rooms import rooms_for_tenant_event, rooms_for_transaction
from app.realtime.server import get_sio
from app.services.alerts import alerts_digest, compute_ops_alerts

logger = logging.getLogger(__name__)

EVENT_CHANNEL = "easypay:event"

_loop: Optional[asyncio.AbstractEventLoop] = None


def bind_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def _mask_recipient(recipient: str) -> str:
    if not recipient:
        return ""
    if "@" in recipient:
        local, _, domain = recipient.partition("@")
        if len(local) <= 2:
            return f"{local[0]}*@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"
    digits = recipient.strip()
    if len(digits) <= 4:
        return "***"
    return f"***{digits[-4:]}"


async def _emit_to_rooms(message: dict[str, Any], rooms: Iterable[str]) -> None:
    sio = get_sio()
    if not sio:
        return
    seen = set()
    for room in rooms:
        if room in seen:
            continue
        seen.add(room)
        await sio.emit(EVENT_CHANNEL, message, room=room)


def _schedule(coro) -> None:
    sio = get_sio()
    if not sio or _loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(coro, _loop)
    except Exception as exc:
        logger.warning("realtime publish failed: %s", exc)


def publish(message: dict[str, Any], rooms: Iterable[str]) -> None:
    from app.core.config import get_settings

    if not get_settings().SOCKETIO_ENABLED:
        return
    _schedule(_emit_to_rooms(message, rooms))


def publish_transaction_status(
    db: Session,
    txn: Transaction,
    *,
    from_status: Optional[str],
    to_status: str,
    note: str = "",
    actor_user_id: Optional[str] = None,
) -> None:
    payer = db.get(Payer, txn.payer_id)
    payer_user_id = payer.user_id if payer else None
    payload = {
        "transaction_id": txn.transaction_id,
        "reference": txn.transaction_reference,
        "from_status": from_status,
        "to_status": to_status,
        "note": note,
        "amount": str(txn.total_amount),
        "currency": txn.currency,
        "payment_channel": txn.payment_channel,
        "payer_id": txn.payer_id,
        "actor_user_id": actor_user_id,
    }
    message = evt.envelope(
        "transaction.status_changed",
        payload,
        tenant_id=txn.transaction_tenant_id,
        entity_type="transaction",
        entity_id=txn.transaction_id,
    )
    publish(message, rooms_for_transaction(txn.transaction_tenant_id, payer_user_id))
    publish_ops_alerts(db, txn.transaction_tenant_id)


def publish_notification_delivery(delivery: NotificationDelivery) -> None:
    payload = {
        "notification_id": delivery.notification_id,
        "channel": delivery.channel,
        "event_type": delivery.event_type,
        "status": delivery.status,
        "recipient_masked": _mask_recipient(delivery.recipient),
        "error_message": delivery.error_message,
        "subject": delivery.subject,
        "body_preview": (delivery.body_preview or "")[:240],
    }
    message = evt.envelope(
        "notification.delivery",
        payload,
        tenant_id=delivery.tenant_id,
        entity_type=delivery.entity_type,
        entity_id=delivery.entity_id,
    )
    publish(message, rooms_for_tenant_event(delivery.tenant_id))


def publish_ops_alerts(db: Session, tenant_id: Optional[str]) -> None:
    snapshot = compute_ops_alerts(db, tenant_id)
    digest = alerts_digest(snapshot)
    payload = {**snapshot, "digest": digest}
    message = evt.envelope("alerts.updated", payload, tenant_id=tenant_id)
    publish(message, rooms_for_tenant_event(tenant_id))
    if tenant_id:
        platform_msg = evt.envelope("alerts.updated", compute_ops_alerts(db, None), tenant_id=None)
        publish(platform_msg, rooms_for_tenant_event(None))


def publish_settlement_event(db: Session, settlement: Settlement, event_type: str, extra: Optional[dict] = None) -> None:
    payload = {
        "settlement_id": settlement.settlement_id,
        "reference": settlement.settlement_reference,
        "status": settlement.status,
        "net_amount": str(settlement.net_amount),
        "currency": settlement.currency,
        **(extra or {}),
    }
    message = evt.envelope(
        event_type,
        payload,
        tenant_id=settlement.tenant_id,
        entity_type="settlement",
        entity_id=settlement.settlement_id,
    )
    publish(message, rooms_for_tenant_event(settlement.tenant_id))
    publish_ops_alerts(db, settlement.tenant_id)
