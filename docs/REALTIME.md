# EasyPay realtime notifications (Socket.IO)

## Architecture

- **Transport:** Socket.IO over WebSocket (polling fallback) at path `/socket.io`.
- **Auth:** Clients pass the REST **access JWT** in the handshake: `auth: { token: "<access_token>" }`. Invalid or missing tokens are rejected at connect time.
- **Rooms:**
  - `user:{user_id}` — payer/staff personal feed (transaction updates for that login).
  - `tenant:{tenant_id}` — council ops feed.
  - `platform:ops` — platform administrators.
- **Event envelope:** All domain events use the single channel `easypay:event` with body:

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "type": "transaction.status_changed",
  "occurred_at": "ISO-8601",
  "tenant_id": "...",
  "entity_type": "transaction",
  "entity_id": "...",
  "payload": { }
}
```

## Event types

| Type | When |
|------|------|
| `transaction.status_changed` | Payment initiated and each status transition |
| `notification.delivery` | After each email/SMS/WhatsApp attempt (SENT / SKIPPED / FAILED) |
| `alerts.updated` | Pending/rejected txns and settlements awaiting approval |
| `settlement.pending_approval` | Settlement calculated |
| `settlement.approved` | Settlement approved |
| `settlement.completed` | Settlement processed |
| `payer.zone_change_decision` | Zone change approved/rejected |

## Production

- Set `SOCKETIO_ENABLED=true` (default).
- For **multiple uvicorn workers**, set `SOCKETIO_REDIS_URL=redis://...` so emits fan-out across processes.
- Align CORS with `CORS_ORIGINS` (same as REST).
- Run: `uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000`

## Frontend

- `RealtimeProvider` connects when logged in.
- Ops shell shows **Live** when connected; alert badge counts refresh on `alerts.updated`.
- Toasts appear when `notification.delivery` events arrive (channel + status).
- Vite dev proxy forwards `/socket.io` to the API.
