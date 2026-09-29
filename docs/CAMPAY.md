# Campay integration

## Payment routing

| Flow | Channel | Campay operation |
|------|---------|------------------|
| Payer MoMo collection | `MOBILE_MONEY` | `POST /collect/` |
| Settlement payout MoMo | `payout_method=MOMO` | `POST /withdraw/` (disburse) |
| Settlement payout bank | `payout_method=BANK` | Campay bank transfer path (default `/withdraw/` + `payment_method=BANK`) |

All Mobile Money collections are forced through the Campay adapter. Non-MoMo channels (CARD/OTHER) do not use Campay.

## API surface

- `POST /api/v1/campay/collect`
- `POST /api/v1/campay/withdraw`
- `POST /api/v1/campay/disburse`
- `POST /api/v1/campay/bank-transfer`
- `GET /api/v1/campay/transactions/{reference}`
- `POST /api/v1/campay/webhook`

## Encrypted provider config (system / super admin)

`PUT /api/v1/providers/campay|email|whatsapp|sms` stores credential JSON with Fernet (`enc:v1:…`) via `app.core.encryption`.

UI: **Platform → Providers (Campay / Email / WA)** — restricted to `SUPER_ADMIN` / `PLATFORM_ADMIN`.

## Settlement process body

```json
{
  "payout_method": "MOMO",
  "momo_number": "2376XXXXXXXX"
}
```

or

```json
{
  "payout_method": "BANK",
  "bank_account_number": "…",
  "bank_account_name": "…",
  "bank_code": "…"
}
```
