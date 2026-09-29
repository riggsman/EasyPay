# EasyPay Frontend UAT Checklist

Manual acceptance checks for the React (JSX) portals.

## Session management
- [ ] Login stores access + refresh tokens
- [ ] Expired access token triggers silent refresh via `/auth/refresh`
- [ ] Failed refresh clears session and returns to login
- [ ] Sign out clears tokens from localStorage

## Public
- [ ] Landing shows EasyPay brand hero + CTAs
- [ ] Register wizard cascading Region → Town → Council
- [ ] Verify receipt works without authentication

## Payer portal (mobile + desktop)
- [ ] Dashboard shows operating area and outstanding/paid
- [ ] Make Payment shows resolved amounts (fee/total) before confirm
- [ ] Payment success shows timeline + receipt number
- [ ] Changing operating area does not move historical payments

## Council console (financial ops)
- [ ] Ops shell: Logo · tenant context · search · alerts · user
- [ ] Nav follows dependency order (Identity → Config → Operations → Finance → Governance)
- [ ] Tenant context is locked (no free-form tenant_id fields)
- [ ] Dashboard figures drill to transactions/settlements/reports
- [ ] Transactions: summary → fee/commission → ledger → state history
- [ ] Pages: payers, obligations, collections, ledger, receipts, settlements, reconciliation, statements, reports, audit, fees, commissions, users, config
- [ ] Settlements calculate / approve / process
- [ ] Reports use transaction geographic snapshots

## Platform console
- [ ] Tenants list + geography tree
- [ ] Cross-tenant payers/transactions/collections
- [ ] Platform dashboard aggregates + alerts
- [ ] Audit trail and system config

## Demo credentials
- admin / admin123
- kumba1_admin / council123
- abctrading / payer123
