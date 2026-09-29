# Backend UI/UX SRS — Applied Mapping

Source: `docs/BACKEND_UI_UX_SRS.md`

| SRS requirement | Implementation |
|---|---|
| Financial ops console (not generic CRUD) | Ops shell + drillable dashboard stats |
| Progressive disclosure | Transaction detail: summary → fee → ledger → timeline |
| Dependency-first nav | Overview → Identity → Config → Operations → Finance → Governance |
| Persistent shell | Logo, tenant/platform context, search, alerts, user |
| tenant_id background | Session JWT + backend resolver; forms omit tenant_id |
| Access + refresh tokens | `src/api/client.js` silent refresh on 401 |
| Argon2 hashing | `app/core/security.py` Argon2id |
| Mobile friendly | Responsive ops-body / public hero breakpoints |
| Tests folders | `backend/tests/{regression,uat}` · `frontend/tests/{regression,uat}` |

Console routes cover: dashboard, alerts, users/roles, revenue, fees, commissions, config, payers, obligations, collections, transactions, ledger, receipts, settlements, reconciliation, statements, reports, audit.
