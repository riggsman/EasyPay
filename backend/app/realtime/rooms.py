from typing import Iterable, Optional, Set


def user_room(user_id: str) -> str:
    return f"user:{user_id}"


def tenant_room(tenant_id: str) -> str:
    return f"tenant:{tenant_id}"


PLATFORM_ROOM = "platform:ops"


def rooms_for_user(user_type: str, tenant_id: Optional[str]) -> Set[str]:
    rooms: Set[str] = set()
    if user_type == "PLATFORM_ADMIN":
        rooms.add(PLATFORM_ROOM)
    if tenant_id and user_type in ("STAFF", "PLATFORM_ADMIN"):
        rooms.add(tenant_room(tenant_id))
    return rooms


def rooms_for_transaction(tenant_id: Optional[str], payer_user_id: Optional[str]) -> Iterable[str]:
    if tenant_id:
        yield tenant_room(tenant_id)
    yield PLATFORM_ROOM
    if payer_user_id:
        yield user_room(payer_user_id)


def rooms_for_tenant_event(tenant_id: Optional[str]) -> Iterable[str]:
    if tenant_id:
        yield tenant_room(tenant_id)
    yield PLATFORM_ROOM
