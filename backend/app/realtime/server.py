from __future__ import annotations

import logging
from typing import Optional

import socketio

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.realtime.auth import authenticate_socket
from app.realtime.rooms import PLATFORM_ROOM, rooms_for_user, tenant_room, user_room

logger = logging.getLogger(__name__)

_sio: Optional[socketio.AsyncServer] = None


def create_socket_server() -> socketio.AsyncServer:
    settings = get_settings()
    client_manager = None
    if settings.SOCKETIO_REDIS_URL:
        client_manager = socketio.AsyncRedisManager(settings.SOCKETIO_REDIS_URL)

    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=settings.socketio_cors_origins,
        client_manager=client_manager,
        logger=False,
        engineio_logger=False,
        ping_interval=25,
        ping_timeout=60,
    )

    @sio.event
    async def connect(sid, environ, auth):
        if not settings.SOCKETIO_ENABLED:
            return False
        token = (auth or {}).get("token") if isinstance(auth, dict) else None
        if not token:
            logger.info("socket connect rejected: missing token sid=%s", sid)
            return False
        try:
            identity = authenticate_socket(token)
        except Exception as exc:
            logger.info("socket connect rejected: %s sid=%s", exc, sid)
            return False

        db = SessionLocal()
        try:
            user = db.get(User, identity.user_id)
            if not user or not user.is_active:
                return False
            tenant_id = user.tenant_id or identity.tenant_id
            user_type = user.user_type
        finally:
            db.close()

        session = {
            "user_id": identity.user_id,
            "user_type": user_type,
            "tenant_id": tenant_id,
            "username": identity.username,
        }
        await sio.save_session(sid, session)
        await sio.enter_room(sid, user_room(identity.user_id))
        for room in rooms_for_user(user_type, tenant_id):
            await sio.enter_room(sid, room)

        await sio.emit(
            "easypay:connected",
            {
                "user_id": identity.user_id,
                "user_type": user_type,
                "tenant_id": tenant_id,
                "rooms": list({user_room(identity.user_id), *rooms_for_user(user_type, tenant_id)}),
            },
            to=sid,
        )
        logger.debug("socket connected user=%s type=%s sid=%s", identity.user_id, user_type, sid)

    @sio.event
    async def disconnect(sid):
        logger.debug("socket disconnected sid=%s", sid)

    @sio.event
    async def subscribe_tenant(sid, data):
        """Platform admins may subscribe to a specific tenant feed for monitoring."""
        session = await sio.get_session(sid)
        if session.get("user_type") != "PLATFORM_ADMIN":
            return {"ok": False, "error": "forbidden"}
        tenant_id = (data or {}).get("tenant_id")
        if not tenant_id:
            return {"ok": False, "error": "tenant_id required"}
        await sio.enter_room(sid, tenant_room(tenant_id))
        return {"ok": True, "tenant_id": tenant_id}

    @sio.event
    async def ping_client(sid):
        return {"ok": True, "room": PLATFORM_ROOM}

    return sio


def get_sio() -> Optional[socketio.AsyncServer]:
    return _sio


def init_socket_server() -> socketio.AsyncServer:
    global _sio
    if _sio is None:
        _sio = create_socket_server()
    return _sio
