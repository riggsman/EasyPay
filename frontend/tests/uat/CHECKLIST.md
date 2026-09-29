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

## Council console
- [ ] Tenant context is locked (no free-form tenant_id fields)
- [ ] Transactions list drills into fee/commission + state history
- [ ] Settlements calculate / approve
- [ ] Reports use transaction geographic snapshots

## Platform console
- [ ] Tenants list
- [ ] Geography tree
- [ ] Platform dashboard aggregates

## Demo credentials
- admin / admin123
- kumba1_admin / council123
- abctrading / payer123
