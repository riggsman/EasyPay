# UI Specification Compliance Matrix (updated)

| Spec area | Screen / behavior | Status | Notes |
|---|---|---|---|
| Financial-first dashboard | Council/Platform dashboard | Met | Drillable stats |
| Progressive disclosure | Transactions, settlements, receipts, obligations, collections, payers | Met | Summary → details → advanced → audit |
| Full drill chain | Transaction drill API + UI | Met | Payer→Obligation→Collection→Txn→Fee→Ledger→Receipt→Settlement |
| App shell | Logo, context, search, alerts, user | Met | Server search + tenant selector (platform) |
| Alerts queue | Alerts page | Met | Pending/rejected/settlement action lists |
| Settlement geo lines | Settlement detail | Met | Line breakdown + approve/process |
| Statements | Tenant + Platform + Payer | Met | Platform uses tenant selector |
| Reports exports | CSV + Excel | Met | |
| Fees/commissions CRUD | Forms + lists | Met | tenant_id from session |
| Users/roles CRUD | Create staff + role list | Met | |
| Audit trail | List + per-txn audit | Met | |
| Payer portal | Dashboard, obligations, pay, history, receipts, statements, notifications, area, profile | Met | |
| Tenant console | Full ops nav | Met | |
| Platform console | Full ops nav + geography/tenants | Met | |
| Session refresh | API client | Met | |
| Argon2 | Backend | Met | |
| Mobile layout | CSS | Met | |
| Tests folders | regression + uat | Met | |

## Remaining future (out of current SRS shell scope)

- Live payment provider webhook UI / fraud monitoring (Advanced Services Phase 10)
- Email/SMS notification delivery adapters
