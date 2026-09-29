# UI Specification Compliance Matrix

| Spec area | Screen / behavior | Status | Notes |
|---|---|---|---|
| Financial-first dashboard | Council/Platform dashboard | Met | Status/exception figures first; drill links |
| Progressive disclosure | Transactions | Met | Summary → fee/commission → ledger → timeline |
| Dependency-first nav | Ops sidebar | Met | Overview → Identity → Config → Operations → Finance → Governance |
| App shell logo | Top bar | Met | EasyPay brand |
| Tenant/Platform selector | Top bar | Met | Locked chip for council; selector for platform |
| Search | Top bar | Met | Filters list pages via outlet context |
| Alerts | Top bar + Alerts page | Met | Pending/rejected/settlement approvals |
| User menu | Top bar | Met | Name + sign out |
| Platform admin | Tenants, geography, users, config | Met | |
| Revenue types | `/tenant/revenue` | Met | tenant_id from session |
| Fees / commissions | `/tenant/fees`, `/commissions` | Met | |
| Payers | `/tenant/payers`, `/platform/payers` | Met | |
| Obligations | `/tenant/obligations` | Met | Snapshot geography from payer zone |
| Collections | Ops collections | Met | |
| Transactions | Ops transactions | Met | Drillable |
| Ledger | Ops ledger | Met | Posting + entries |
| Receipts + verify | Ops receipts + public `/verify` | Met | |
| Settlements | Ops settlements | Met | Calculate/approve/process |
| Reconciliation | Ops reconciliation | Met | Exception view |
| Statements | Ops statements (tenant) | Met | Platform requires tenant context |
| Reports | Ops reports | Met | Snapshot geography |
| Audit | Ops audit | Met | |
| System config | Ops config | Met | |
| Session access+refresh | API client | Met | Silent refresh on 401 |
| Argon2 passwords | Backend security | Met | |
| Mobile layout | CSS breakpoints | Met | Stacked ops aside on small screens |
| Tests folders | regression + uat | Met | Backend 10 tests; frontend regression + checklist |

## Known intentional limits (not full product depth)

- Provider response payloads / fraud monitoring screens not built (Phase 10 advanced)
- Statement PDF/Excel export UI not yet wired (API totals + lines available)
- Platform statements require choosing a tenant context first
- Search is client-side filter on loaded lists (not full-text server search)
