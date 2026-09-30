# EasyPay Implementation Plan

**Stack:** FastAPI (backend) · MySQL (database) · React + JSX (frontend)  
**Source:** EasyPay SRS v1.0 / Zone-Aware SRS v1.1  
**Architecture:** Multi-tenant, zone-aware, dependency-first  
**Financial model:** Immutable transactions + double-entry ledger  

---

## Guiding Rules

1. **Dependency-first** — no module is production-ready until its upstream dependencies are implemented and tested.
2. **Never rewrite history** — changing a payer’s operating zone must never alter historical transactions, receipts, settlements, statements, or ledger entries.
3. **Backend owns truth** — the frontend never decides council/tenant/fee context; the API resolves and validates it.
4. **Shared DB, tenant isolation** — one MySQL database; every tenant-scoped query filters by `tenant_id` (and related isolation middleware).
5. **Snapshot on post** — transactions, obligations, collections, and receipts store immutable geographic + tenant context at creation time.

---

## Recommended Monorepo Layout

```
easypay/
├── backend/                 # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # config, security, deps, tenant middleware
│   │   ├── db/              # session, base, migrations helpers
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response
│   │   ├── api/             # routers by domain
│   │   ├── services/        # business logic
│   │   ├── repositories/    # data access
│   │   └── utils/           # audit, receipts QR, exports
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # React (Vite) — JSX only, no TypeScript
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   │   ├── public/      # landing, verify, register, login
│   │   │   ├── payer/       # payer portal
│   │   │   ├── tenant/      # council admin
│   │   │   └── platform/    # platform admin
│   │   ├── routes/
│   │   ├── styles/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── docs/
    └── IMPLEMENTATION_PLAN.md
```

---

# PART A — BACKEND IMPLEMENTATION

Implement and test each phase before starting the next. Frontend work for a phase may begin only after that phase’s APIs are stable.

---

## Phase 0 — Project Foundation

**Goal:** Runnable FastAPI app with MySQL, migrations, config, and CI-ready structure.

### Deliverables

| Item | Detail |
|------|--------|
| FastAPI app skeleton | `app/main.py`, CORS, health `/health` |
| Config | `pydantic-settings` from `.env` (DB URL, JWT secret, CORS origins) |
| MySQL connection | SQLAlchemy 2.x + PyMySQL/mysqlclient |
| Alembic | Initial empty migration pipeline |
| Auth stubs | Password hashing (bcrypt/argon2), JWT utilities |
| Testing | pytest + httpx `AsyncClient` / `TestClient` |
| Docker Compose (optional) | `mysql` + `api` for local/dev |

### Tech choices

- SQLAlchemy 2.0 ORM
- Alembic for schema migrations
- Pydantic v2 schemas
- JWT (access + refresh) for authentication
- Soft deletes / status flags where SRS uses `status`

### Exit criteria

- `GET /health` returns 200
- Alembic can create/drop schema against MySQL
- Env-based DB config works

---

## Phase 1 — Platform Foundation & Geography

**SRS levels:** Platform · Geographic Structure · Tenant · User Identity · Auth · RBAC · Tenant Isolation · Audit · System Configuration

### 1.1 Database tables (order of creation)

```
platforms
geographic_units
tenants
tenant_geographic_units
users
user_identities          # email / phone / username bindings
roles
permissions
role_permissions
user_roles               # scoped by platform or tenant
audit_events
system_configurations
```

### 1.2 Core entity fields (from SRS)

**platforms**  
`platform_id`, `platform_code`, `platform_name`, `legal_name`, `registration_number`, `email`, `phone`, `address`, `default_currency`, `status`, `created_at`, `updated_at`

**geographic_units**  
`geographic_unit_id`, `parent_id` (self-FK), `unit_code`, `unit_name`, `unit_type` (COUNTRY | REGION | DIVISION | TOWN | MUNICIPALITY | COUNCIL | ZONE | OTHER), `country_code`, `status`, `created_at`, `updated_at`

**tenants**  
`tenant_id`, `tenant_code`, `organization_type`, `organization_name`, `registration_number`, `email`, `phone_number`, `location`, `momo_number`, `bank_account_number`, `currency`, `status`, `verification`, `created_at`, `updated_at`

**tenant_geographic_units**  
`tenant_geographic_unit_id`, `tenant_id`, `geographic_unit_id`, `relationship_type`, `is_primary`, `status`, `effective_from`, `effective_to`, `created_at`, `updated_at`

### 1.3 API modules

| Router | Endpoints (illustrative) |
|--------|--------------------------|
| `auth` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` |
| `platforms` | CRUD platform (platform-admin only) |
| `geography` | Tree CRUD; `GET /geography/children?parent_id=`; hierarchy validation |
| `tenants` | CRUD tenants; map to geographic units |
| `users` | Invite/create users; assign roles |
| `rbac` | Roles & permissions management |
| `audit` | Query audit events (read-only for authorized roles) |
| `config` | System configuration key-value |

### 1.4 Cross-cutting services

- **TenantIsolationMiddleware / dependency** — resolve `tenant_id` from JWT claims; reject cross-tenant access
- **RBAC dependency** — `require_permission("tenants:write")` etc.
- **AuditService** — write `audit_events` on create/update/status change (actor, entity, before/after, reason)
- **GeographyService.validate_hierarchy(path)** — ensure parent–child integrity (backend-only; frontend cascade is not enough)

### 1.5 Seed data (Cameroon / Southwest example)

- Country → Region → Division → Town → Councils (Kumba 1/2/3) as `geographic_units`
- Three tenants mapped via `tenant_geographic_units`
- Platform admin user + sample council admin roles

### Exit criteria

- Hierarchical geography CRUD with backend validation
- Tenant ↔ council zone mapping works
- JWT login + RBAC blocks unauthorized routes
- Audit trail written for tenant/user mutations

---

## Phase 2 — Payer Account & Operating Zone

**SRS:** Payer registration · Current zone · Zone history · Zone change (immediate / approval)

### 2.1 Tables

```
payers
payer_geographic_history
zone_change_requests     # when approval_required
```

**payers**  
`payer_id`, `tenant_id` (derived from current zone mapping — or nullable until zone set), `payer_reference`, `payer_type`, `full_name`, `business_name`, `identification_type`, `identification_number`, `email`, `phone_number`, `address`, `current_geographic_unit_id`, `user_id` (FK to users), `status`, `created_at`, `updated_at`

**payer_geographic_history**  
`payer_geographic_history_id`, `payer_id`, `geographic_unit_id`, `tenant_id`, `effective_from`, `effective_to`, `change_reason`, `change_source`, `changed_by`, `status`, `created_at`

### 2.2 Services

- **PayerRegistrationService** — create user + payer + initial history row in one transaction; resolve `tenant_id` from selected council geographic unit via `tenant_geographic_units`
- **ZoneChangeService** — close prior history (`effective_to`), open new row, update `current_geographic_unit_id`; respect tenant config `zone_change_mode` = `IMMEDIATE` | `APPROVAL_REQUIRED`
- **ZoneChangeApprovalService** — PENDING → UNDER_REVIEW → APPROVED | REJECTED

### 2.3 API

| Method | Path | Notes |
|--------|------|-------|
| POST | `/payers/register` | Public; multi-step payload or single validated body |
| POST | `/auth/payer/login` | Payer-scoped JWT claims |
| GET | `/payers/me` | Profile + current zone ancestry |
| PATCH | `/payers/me` | Identity/contact updates |
| GET | `/payers/me/operating-area` | Current zone + history |
| POST | `/payers/me/operating-area/change` | Request/apply zone change |
| GET/POST | `/tenants/{id}/zone-change-requests` | Council review queue |

### Exit criteria

- Registration requires valid hierarchical zone
- Zone change never mutates historical financial rows (none exist yet — enforce via service contract + tests)
- History table always has open-ended current row

---

## Phase 3 — Revenue Configuration

**SRS:** Revenue types · Payment channels · Fees · Commissions · Financial periods

### 3.1 Tables

```
revenue_types
payment_channels
financial_periods
fee_configurations
fee_bands
commission_agreements
```

Fee/revenue applicability dimensions (SRS):  
`tenant_id` + `geographic_unit_id` (optional) + `revenue_type_id` + `payment_channel_id` + amount band

### 3.2 Services

- **FeeCalculationService** — given context, return service fee
- **CommissionCalculationService** — contractual commission for tenant/channel
- Config CRUD with effective dating (`effective_from` / `effective_to`)

### 3.3 API

- Tenant-scoped CRUD for revenue types, channels, periods, fees, commissions
- `POST /fees/preview` — preview fee for amount + channel + revenue (used by payment UI later)

### Exit criteria

- Different councils can have different fees for the same revenue type
- Preview endpoint is deterministic and covered by unit tests

---

## Phase 4 — Obligations

**SRS:** Zone-aware obligations with geographic + tenant snapshot fields

### 4.1 Tables

```
obligations
```

Required snapshot fields: `geographic_unit_id`, `tenant_id`, plus payer, revenue type, period, amount, balance, status

### 4.2 Services

- Create/assign obligations scoped to payer’s authorized zone/tenant
- List obligations for payer: only those matching authorized context
- Balance updates only via payment/adjustment flows (Phase 5–6), not arbitrary edits after posting

### 4.3 API

- Tenant admin: create/list/update obligations
- Payer: `GET /payers/me/obligations`

### Exit criteria

- Obligation retains council/zone even if payer later moves
- Payer cannot see another council’s obligations

---

## Phase 5 — Collection & Transaction Engine

**SRS:** Collection · Transaction · State machine · Idempotency · Fee/commission · Payment context resolution

### 5.1 Tables

```
collections
transactions
transaction_contexts      # optional dedicated snapshot table
transaction_events        # timeline / state transitions
idempotency_keys
```

**Transaction create fields (SRS):**  
`transaction_id`, `transaction_reference`, `correlation_id`, `idempotency_key`, `payer_id`, `tenant_id`, `geographic_unit_id`, `obligation_id`, `revenue_type_id`, `amount`, `currency`, `payment_channel`, `status`, `initiated_at`  
Plus fees/commission amounts as posted at calculation time.

### 5.2 State machine

```
INITIATED → PROCESSING → DEBITED → CREDITED → SETTLED
                                              ↘ FAILED
         (FAILED is also reachable from INITIATED / PROCESSING / DEBITED;
          SETTLED and FAILED are peer terminal outcomes)
```

Persist every transition in `transaction_events` for UI timeline.

### 5.3 PaymentContextResolver (critical)

```
authenticated_user
  → payer
  → current_operating_area
  → authorized_council/tenant
  → revenue type
  → obligation
  → fee + commission
```

**Security rule:** Ignore client-supplied `council_id` / `tenant_id` for authorization. Re-resolve from session + DB. Reject mismatches.

### 5.4 API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/payments/resolve` | Return payable context + amounts for UI |
| POST | `/payments/initiate` | Idempotent create transaction |
| GET | `/payments/{id}` | Status + timeline |
| POST | `/payments/{id}/confirm` | Advance processing (or webhook later) |

### Exit criteria

- Malicious `council_id` in body cannot pay under wrong tenant
- Idempotency key prevents duplicate charges
- Transaction stores immutable `transaction_geographic_unit_id` / `transaction_tenant_id`

---

## Phase 6 — Ledger

**SRS:** Double-entry · Accounts · Posting · Reversals · Adjustments

### 6.1 Tables

```
financial_accounts
ledger_entries          # immutable; balanced debit/credit
ledger_postings         # groups entries for one event
reversals
adjustments
```

### 6.2 Rules

- Every successful financial event posts balanced entries
- No update/delete of posted ledger rows — reverse with compensating entries
- Ledger entries also store tenant + geographic snapshot where relevant

### 6.3 API

- Internal service API primarily; admin read endpoints for account balances and entry inquiry

### Exit criteria

- Trial balance remains zero per posting batch
- Reversal creates linked compensating posting

---

## Phase 7 — Receipts & Verification

**SRS:** Official receipts · QR · Public verify · Revocation

### 7.1 Tables

```
receipts
receipt_verifications   # optional audit of verify attempts
```

Receipt fields: council, payer (display), revenue, amount, service fee, total, transaction ref, receipt number, payment date, opaque `verification_token`, status

### 7.2 Services

- Generate receipt on SETTLED (or CREDITED per policy)
- QR encodes `/v/{opaque-token}` only — never raw IDs/amounts in query string
- Public verify returns masked payer data

### 7.3 API

| Method | Path | Auth |
|--------|------|------|
| GET | `/receipts/{id}` | Payer/tenant |
| GET | `/receipts/{id}/pdf` | Authenticated |
| GET | `/public/verify/{token}` | Public |
| POST | `/public/verify` | Public (number/code) |
| POST | `/receipts/{id}/revoke` | Authorized admin |

### Exit criteria

- Opaque token verification works without login
- Revoked receipts return NOT VERIFIED

---

## Phase 8 — Settlement & Reconciliation

**SRS:** Settlement calculation · Approval · Processing · Reconciliation

### 8.1 Tables

```
settlements
settlement_lines        # can break down by geographic unit when needed
settlement_approvals
reconciliation_records
```

Settlement is primarily tenant-based; lines can attribute geographic units for reporting.

### 8.2 Workflow

```
CALCULATED → PENDING_APPROVAL → APPROVED → PROCESSING → COMPLETED
                              ↘ REJECTED
```

### 8.3 API

- Tenant/platform settlement list, detail, approve, process
- Reconciliation match/unmatch tools

### Exit criteria

- Net settlement = gross − fees − commission (per agreement)
- Historical settlement lines never re-map after payer zone change

---

## Phase 9 — Reporting, Statements, Dashboards, Exports

**SRS:** Statements · Dashboards · Reports · PDF/Excel · Geographic analytics

### 9.1 Capabilities

- Filters: Region, Town, Council, Zone, Revenue Type, Payer, Date, Channel, Status
- Aggregations always keyed off **transaction snapshot geography**, not payer current zone
- PDF/Excel export jobs (sync first; async queue later)

### 9.2 API

- `/reports/collections`, `/reports/revenue`, `/statements/{tenant|payer}`
- `/dashboards/platform`, `/dashboards/tenant`, `/dashboards/payer`
- `/exports` (PDF/XLSX)

### Exit criteria

- Drill-down Southwest → Kumba → Kumba 1 uses snapshot fields
- Export matches on-screen totals

---

## Phase 10 — Advanced Services

**SRS:** Notifications · Payment providers · Integrations · Fraud · Analytics

### 10.1 Order within phase

1. Notification stubs (email/SMS interfaces)
2. Payment provider adapters (MoMo, bank, card) + webhooks
3. External integration hooks
4. Fraud monitoring rules
5. Advanced analytics

### Exit criteria

- Provider webhook can advance transaction state machine safely (signature verify + idempotency)

---

## Backend Cross-Cutting Checklist (every phase)

- [ ] Alembic migration reviewed
- [ ] Pydantic schemas with clear validation errors
- [ ] RBAC + tenant isolation on all mutating routes
- [ ] Audit events for sensitive actions
- [ ] Unit tests for services; API tests for authz boundaries
- [ ] OpenAPI tags kept clean for frontend codegen-by-hand consumption

### Suggested backend package libs

`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pymysql`, `cryptography`/`passlib`, `python-jose` or `PyJWT`, `pydantic-settings`, `python-multipart`, `reportlab` or `weasyprint` (PDF), `openpyxl` (Excel), `qrcode`, `pytest`, `httpx`

---

# PART B — FRONTEND IMPLEMENTATION

**Stack:** React (Vite) · **JSX only** (no TypeScript) · React Router · fetch/axios API client  

Frontend phases align to backend readiness. Prefer three app areas under one SPA with route guards:

1. **Public** — landing, register, login, verify receipt  
2. **Payer portal** — obligations, pay, receipts, zone  
3. **Admin** — platform admin + tenant/council admin  

---

## FE Phase 0 — App Shell

### Deliverables

- Vite + React JSX project
- Routing (`react-router-dom`)
- Auth context (token storage, login/logout, role claims)
- API client with base URL + Bearer header + 401 handling
- Layouts: `PublicLayout`, `PayerLayout`, `TenantLayout`, `PlatformLayout`
- Shared UI primitives (forms, tables, alerts) — keep lean; no card-heavy dashboard look on public landing
- Env: `VITE_API_BASE_URL`

### Exit criteria

- Protected routes redirect to login
- Role-based route groups work with mock JWT if needed

---

## FE Phase 1 — Public Landing & Auth Screens

**Depends on:** Backend Phase 1 (auth + geography read) and Phase 2 (register) for live data

### Pages

| Route | Purpose |
|-------|---------|
| `/` | Public landing (hero, how it works, supported councils, FAQ, footer) |
| `/verify` | Receipt verification (no auth) |
| `/register` | Multi-step payer registration |
| `/login` | Payer (and optionally shared) login |
| `/admin/login` | Staff login if separated |

### Landing content (SRS)

- Brand-forward hero: pay council levies
- CTAs: Create Account, Sign In, Verify Receipt
- How it works: Register → Select Zone → View Levy → Pay → Verify
- Optional cascading “Find Your Council” (Region → Town → Council)

### Registration wizard

1. Account / identity  
2. Business / activity  
3. Operating location (cascading selects from `GET /geography/children`)  
4. Confirm operating council  

Client validation + **server validation** of hierarchy.

### Exit criteria

- Hierarchical selectors load children from API
- Register → login → redirect to payer dashboard

---

## FE Phase 2 — Payer Portal

**Depends on:** Backend Phases 2–5 (and 7 for receipts)

### Navigation

Dashboard · My Profile · Operating Area · My Obligations · Make Payment · Payment History · Receipts · Statements · Notifications · Support

### Key screens

| Screen | Behavior |
|--------|----------|
| Dashboard | Greeting, current operating area, outstanding/paid summaries, recent obligations |
| Profile | Identity vs operating info sections; history list |
| Change Operating Area | Cascading new zone + reason; show pending approval state |
| Obligations | Table: revenue, council, period, amount, balance, status |
| Make Payment | Resolve context → show amounts → channel → confirmation |
| Payment success | TXN + receipt refs; timeline; links to view/download/verify |
| Payment history | List + detail with state timeline |
| Receipts | View/download; link to public verify |

### Payment UX rules

- Always show operating area before confirm
- Allow “Change” zone before pay only via proper zone-change flow; then **re-call** `/payments/resolve`
- Confirmation screen must show amount, service fee, total, channel
- Never trust UI-only council selection for submit payload beyond what API already resolved

### Exit criteria

- End-to-end pay happy path against backend
- Zone change request UI reflects IMMEDIATE vs APPROVAL modes

---

## FE Phase 3 — Tenant (Council) Admin

**Depends on:** Backend Phases 1–5, 8–9 as features land

### Screens

- Council dashboard (today’s collections, success/pending/rejected, outstanding settlement)
- Revenue breakdown
- Payers list (tenant-scoped)
- Obligations management
- Transactions inquiry
- Zone-change approval queue
- Settlements approve/process
- Reports with geographic filters (locked to tenant’s zone by default)

### Security UX

- No UI affordance to switch to another council unless user has multi-tenant grants
- All lists come from tenant-scoped APIs

---

## FE Phase 4 — Platform Admin

**Depends on:** Backend Phases 1 + 9

### Screens

- Platforms / tenants CRUD
- Geographic hierarchy manager (tree editor)
- Tenant ↔ geographic mapping
- Users & RBAC
- System configuration
- Geographic drill-down dashboard: Region → Town → Council → collections
- Cross-tenant reports & exports

---

## FE Phase 5 — Reporting & Exports UX

- Filter bars (geography cascade, dates, revenue, channel, status)
- Drillable aggregates → transaction list
- Download PDF/Excel

---

## FE Phase 6 — Polish & Advanced

- Notifications center
- Provider redirect/callback pages for MoMo/card
- Public verify QR scanner (camera) where feasible
- Responsive layouts for mobile payers
- Loading/error empty states; idempotent submit buttons (disable on in-flight)

---

# PART C — DELIVERY SEQUENCE (BACKEND FIRST)

| Sprint / slice | Backend | Frontend |
|----------------|---------|----------|
| S0 | Phase 0 foundation | FE Phase 0 shell |
| S1 | Phase 1 platform + geography + auth + RBAC | Geography admin + staff login (minimal) |
| S2 | Phase 2 payer + zone | Public landing, register, login, operating area |
| S3 | Phase 3–4 config + obligations | Payer obligations + tenant revenue config UI |
| S4 | Phase 5 transactions | Make payment + history timeline |
| S5 | Phase 6–7 ledger + receipts | Receipts + public verify |
| S6 | Phase 8 settlements | Tenant settlement screens |
| S7 | Phase 9 reporting | Dashboards, statements, exports |
| S8 | Phase 10 providers & notifications | Provider callbacks + notification UI |

**Rule:** For each slice, ship and test backend APIs (OpenAPI + pytest) before wiring the matching React screens.

---

# PART D — CRITICAL TEST MATRIX

| Case | Expected |
|------|----------|
| Payer in Kumba 1 pays, then moves to Kumba 3 | Historical TXN/receipt still Kumba 1 |
| Report by council after move | Old payment stays under Kumba 1 aggregates |
| Client sends wrong `council_id` on pay | 403/422; no transaction created |
| Invalid geography parent/child on register | 422 from backend |
| Duplicate `idempotency_key` | Same transaction returned; no double charge |
| Tenant user of Kumba 1 lists payers | Never sees Kumba 2 rows |
| Public verify with opaque token | Masked success payload |
| Revoked receipt verify | NOT VERIFIED |
| Ledger posting | Debits = credits |
| Zone change approval mode | Status PENDING until council approves |

---

# PART E — API CONVENTIONS (for frontend contract)

- Base path: `/api/v1`
- Auth: `Authorization: Bearer <access_token>`
- Errors: `{ "detail": "...", "code": "ZONE_MISMATCH" }`
- Money: integer minor units **or** decimal strings — pick one globally (recommend **decimal strings** in XAF without cents ambiguity, documented in OpenAPI)
- Pagination: `?page=&page_size=`
- Idempotency: header `Idempotency-Key` on payment initiate
- Timestamps: ISO-8601 UTC

---

# PART F — DEFINITION OF DONE (per phase)

1. MySQL migrations applied  
2. Service + API tests green  
3. OpenAPI updated  
4. Tenant isolation + RBAC verified  
5. Audit events for sensitive writes  
6. Matching React JSX screens only after API contract is stable  
7. Manual or automated check of the historical-geography invariant where financial data exists  

---

## Immediate Next Step

Start **Backend Phase 0 + Phase 1**: scaffold FastAPI project, MySQL models for `platforms`, `geographic_units`, `tenants`, `tenant_geographic_units`, users/RBAC, Alembic migrations, and auth endpoints — then seed the Cameroon / Southwest / Kumba council tree.
