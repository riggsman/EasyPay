import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def write_audit(
    db: Session,
    *,
    actor_user_id: Optional[str],
    tenant_id: Optional[str],
    entity_type: str,
    entity_id: str,
    action: str,
    before: Any = None,
    after: Any = None,
    reason: Optional[str] = None,
    source: str = "API",
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=json.dumps(before, default=str) if before is not None else None,
        after_json=json.dumps(after, default=str) if after is not None else None,
        reason=reason,
        source=source,
    )
    db.add(event)
    return event
