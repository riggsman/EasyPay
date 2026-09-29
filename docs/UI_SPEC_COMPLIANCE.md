# UI Specification Compliance Matrix

| Spec area | Screen / behavior | Status | Notes |
|---|---|---|---|
| Financial-first dashboard | Council/Platform dashboard | Met | Drillable stats → lists |
| Progressive disclosure | Txn, settlement, receipt, payer, obligation, collection, ledger entries | Met | Summary → details → advanced → audit on money path |
| Full drill chain | Transaction drill API + UI + ledger/receipt links | Met | Payer→Obligation→Collection→Txn→Fee→Ledger→Receipt→Settlement |
| App shell | Logo, context, search, alerts, user, Live | Met | |
| Alerts queue | Alerts page + realtime refresh | Met | |
| Settlement geo lines + MoMo/Bank payout | Settlement detail | Met | Campay disburse / bank |
| Statements | Tenant + Platform + Payer | Met | |
| Reports exports | Collections CSV/XLSX, settlements CSV, audit CSV | Met | |
| Fees/commissions CRUD | Forms + lists | Met | Platform nav includes fees/commissions |
| Users/roles CRUD | Create staff + role list | Met | |
| Audit trail | List + per-txn audit + CSV export | Met | |
| Payer portal | Full set including real notification inbox | Met | `/ops/my-notifications` delivery log |
| Tenant console | Full dependency-first ops nav | Met | |
| Platform console | Ops + revenue config + obligations + providers | Met | Parity with tenant operations |
| Server list search | Payers, transactions, receipts, ledger, audit | Met | `q` / filters on APIs |
| Pagination | Primary ops lists | Met | `{items,page,total,…}` + PaginationBar |
| Email/SMS/WhatsApp modules | Dispatcher + encrypted provider UI | Met | Platform Providers page |
| SMS toggleable | Env master + ops toggle + encrypted SMS credentials | Met | |
| Socket.IO realtime | Events for txn/alerts/notifications | Met | |
| Campay MoMo | All MOBILE_MONEY via Campay | Met | |
| Encrypted provider config | Campay / Email / WhatsApp / SMS | Met | System/super admin only |
| Argon2 + refresh sessions | Auth | Met | |
| Mobile layout | CSS | Met | |
| Tests folders | regression + uat | Met | |

## Explicitly out of current shell scope

- Live payment-provider fraud monitoring console (Advanced Services)
- Geographic Region→Town→Council heatmap dashboard (future analytics)

## Verification

- Backend: `pytest backend/tests`
- Frontend: `npm run build`
