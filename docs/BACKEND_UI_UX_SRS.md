# Financial Collection Platform — Production Backend UI/UX SRS

Document Type: UI/UX + Frontend Engineering SRS  
Architecture: Multi-Tenant Financial Collection Platform  
Design Approach: Dependency-First  
UI Type: Responsive Web-Based Backend Console  
Design Priority: Financial correctness, operational clarity, security, traceability and usability  
Version: 1.0

## Core UX principle

Every important financial figure must be explainable, traceable and drillable.

## Dependency-first UI order

01 Identity → 02 Platform/Tenant → 03 Access Control → 04 Configuration → 05 Revenue Setup → 06 Payers/Obligations → 07 Collections → 08 Transactions → 09 Ledger → 10 Receipts → 11 Settlement → 12 Reconciliation → 13 Statements → 14 Reports → 15 Dashboards

## Application shell

Persistent top bar: Logo · Tenant/Platform context · Search · Alerts · User  
Sidebar grouped by Operations / Configuration / Finance / Governance  
Progressive disclosure: Summary → Details → Advanced → Audit Trail

## Non-functional UI rules

- Required fields shown; system fields (`tenant_id`, snapshot geography) resolved in background from session/backend
- Access + refresh token session management
- Argon2 password hashing
- Mobile-friendly while respecting desktop ops layout
- Tests under `tests/regression` and `tests/uat`
