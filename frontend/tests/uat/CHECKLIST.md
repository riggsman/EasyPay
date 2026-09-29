# EasyPay Frontend UAT Checklist

## Session management
- [x] Login stores access + refresh tokens
- [x] Expired access token triggers silent refresh via `/auth/refresh`
- [x] Failed refresh clears session and returns to login
- [x] Sign out clears tokens from localStorage

## Public
- [x] Landing shows EasyPay brand hero + CTAs
- [x] Register wizard cascading Region → Town → Council
- [x] Verify receipt works without authentication

## Payer portal
- [x] Dashboard: operating area, outstanding/paid
- [x] Obligations list
- [x] Make Payment with resolve → confirm amounts
- [x] Payment detail: timeline + fee disclosure + zone snapshot
- [x] Receipts + link to public verify
- [x] Statements
- [x] Notifications
- [x] Operating area change + history
- [x] Profile

## Council console
- [x] Ops shell: Logo · tenant context · search · alerts · user
- [x] Dependency-first nav
- [x] Drillable dashboard
- [x] Actionable alerts queues
- [x] Server search results
- [x] Users & roles create
- [x] Revenue / fees / commissions forms (no tenant_id fields)
- [x] Payers → detail drill
- [x] Obligations create + detail drill
- [x] Collections detail
- [x] Transactions progressive disclosure + full chain + audit
- [x] Ledger posting entries
- [x] Receipts expand + verify
- [x] Settlements + geographic lines + approve/process
- [x] Reconciliation exceptions
- [x] Statements
- [x] Reports with CSV/Excel export
- [x] Audit trail

## Platform console
- [x] Tenant selector
- [x] Tenants + geography
- [x] Shared ops screens with tenant filter
- [x] Statements (requires tenant selection)
- [x] Settlements calculate with tenant context

## Demo credentials
- admin / admin123
- kumba1_admin / council123
- abctrading / payer123
