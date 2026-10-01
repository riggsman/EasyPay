import asyncio
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.realtime.publisher import bind_event_loop
from app.realtime.server import init_socket_server

CACHE_TTL_HEADER = "X-EasyPay-Cache-TTL"


class ClientCacheTtlMiddleware(BaseHTTPMiddleware):
    """Attach the platform client-cache TTL so browsers can refresh their local value."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ttl = 15 * 60
        db = SessionLocal()
        try:
            from app.services.client_cache import get_client_cache_ttl_seconds

            ttl = get_client_cache_ttl_seconds(db)
        except Exception:  # noqa: BLE001
            ttl = 15 * 60
        finally:
            db.close()
        response.headers[CACHE_TTL_HEADER] = str(ttl)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    bind_event_loop(asyncio.get_running_loop())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)
    app.add_middleware(ClientCacheTtlMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[CACHE_TTL_HEADER],
    )
    app.include_router(api_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "app": settings.APP_NAME, "realtime": settings.SOCKETIO_ENABLED}

    return app


fastapi_app = create_app()

if get_settings().SOCKETIO_ENABLED:
    sio = init_socket_server()
    asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path=get_settings().SOCKETIO_PATH)
else:
    asgi_app = fastapi_app

# Uvicorn entrypoint: app.main:asgi_app
app = asgi_app
