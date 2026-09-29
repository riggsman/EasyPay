from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


def envelope(
    event_type: str,
    payload: dict[str, Any],
    *,
    tenant_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": str(uuid4()),
        "type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
    }
