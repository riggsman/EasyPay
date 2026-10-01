Software Requirements Specification (SRS)

Financial Collection, Payment, Settlement & Revenue Management Platform

Document Version: 1.0
Architecture Approach: Multi-Tenant, Dependency-First
Database Model: Shared Database with Tenant Isolation
Currency: Multi-Currency Capable
Primary Financial Model: Immutable Transactions + Double-Entry Ledger
Document Status: System Design Specification

---

1. Introduction

1.1 Purpose

This SRS defines the requirements for a multi-tenant financial collection platform that enables organizations such as councils, government institutions, businesses, associations and other entities to collect payments from citizens, businesses and organizations.

The platform operator acts as the collection platform and financial intermediary.

The system shall:

- register and manage tenants;
- register and manage payers;
- define revenue types and payment obligations;
- initiate and process collections;
- calculate service fees;
- calculate contractual commissions;
- record complete transaction lifecycles;
- generate official verifiable receipts;
- settle collected funds to tenants;
- maintain balanced financial records;
- generate tenant and platform statements;
- support reconciliation;
- provide dashboards;
- provide PDF and Excel exports;
- maintain complete audit trails;
- enforce role-based and tenant-based access control.

---

2. Dependency-First Architecture

The implementation shall follow this dependency chain:

FOUNDATION
   │
   ├── Platform
   ├── Tenant
   ├── User Identity
   ├── Authentication
   ├── RBAC
   └── Tenant Isolation
          │
          ▼
CONFIGURATION
   │
   ├── System Configuration
   ├── Revenue Types
   ├── Payment Channels
   ├── Fee Configuration
   ├── Commission Agreements
   └── Financial Periods
          │
          ▼
MASTER DATA
   │
   ├── Payers
   ├── Obligations
   ├── Accounts
   └── References
          │
          ▼
TRANSACTION ENGINE
   │
   ├── Collection
   ├── Transaction
   ├── Transaction State Machine
   ├── Fee Calculation
   ├── Commission Calculation
   └── Financial Ledger
          │
          ▼
PAYMENT COMPLETION
   │
   ├── Receipt
   ├── QR Verification
   ├── Reversal
   └── Adjustment
          │
          ▼
SETTLEMENT
   │
   ├── Settlement Calculation
   ├── Approval
   ├── Settlement Processing
   └── Reconciliation
          │
          ▼
REPORTING
   │
   ├── Statements
   ├── Dashboards
   ├── Reports
   ├── PDF Export
   └── Excel Export
          │
          ▼
ADVANCED SERVICES
   │
   ├── Notifications
   ├── Payment Providers
   ├── External Integrations
   ├── Fraud Monitoring
   └── Advanced Analytics

No dependent module should be considered production-ready until its upstream dependencies are implemented and tested.

---

3. Dependency Levels

Level 0 — Platform Foundation

These are the lowest-level dependencies.

Required before any financial functionality.

Components

1. Platform
2. Tenant
3. User
4. User Identity
5. Authentication
6. Role-Based Access Control
7. Tenant Isolation
8. Audit Framework
9. System Configuration

---

4. Level 1 — Platform and Tenant Management

4.1 Platform

The platform represents the operator of the collection system.

Required attributes

- platform_id
- platform_code
- platform_name
- legal_name
- registration_number
- email
- phone
- address
- default_currency
- status
- created_at
- updated_at

---

5. Tenant Management

A tenant represents an organization using the platform to collect revenue.

Examples:

- Local Council
- Government Department
- Association
- Private Company
- Institution

Tenant attributes

- tenant_id
- tenant_code
- organization_type
- organization_name
- registration_number
- email
- phone_number
- location
- momo_number
- bank_account_number
- currency
- status
- verification


Financial Collection Platform

Zone-Aware Multi-Tenant Backend and Payer Portal SRS

Version: 1.1
Context: Cameroon / Southwest Region
Architecture: Multi-Tenant, Zone-Aware Financial Collection Platform
Design Approach: Dependency-First
Primary Users: Platform Administrators, Councils/Tenants, Payers
Financial Principle: Historical transactions retain the organizational/location context that existed when the transaction occurred.

---

1. Change Summary

The platform shall now support geographical/council-based collection.

A payer must belong to a current operating zone/council.

For example:

Southwest Region
    │
    └── Kumba
          │
          ├── Kumba 1 Council
          ├── Kumba 2 Council
          └── Kumba 3 Council

A payer registering on the platform shall select the council/zone where they currently operate.

The selected zone determines the default context for:

- revenue types;
- applicable levies;
- payment obligations;
- collection;
- payment processing;
- receipts;
- statements;
- reporting.

A payer may later change their operating zone.

However:

«Changing the payer's current zone must never alter historical transactions, receipts, settlements or statements.»

---

2. Updated Dependency Architecture

The dependency chain becomes:

PLATFORM
   ↓
GEOGRAPHICAL STRUCTURE
   ↓
TENANT / COUNCIL
   ↓
USER IDENTITY
   ↓
PAYER ACCOUNT
   ↓
PAYER CURRENT ZONE
   ↓
REVENUE CONFIGURATION
   ↓
OBLIGATION
   ↓
COLLECTION
   ↓
TRANSACTION
   ↓
LEDGER
   ↓
RECEIPT
   ↓
SETTLEMENT
   ↓
STATEMENT / REPORT

This is an important change.

The geographical structure must exist before payer registration and payment configuration.

---

3. New Domain Concept: Administrative / Collection Geography

The system shall distinguish between:

1. geographical location;
2. council/tenant;
3. payer's current operating location;
4. historical transaction location.

These must not be treated as the same thing.

---

4. Geographic Hierarchy

The platform shall support a configurable hierarchy.

Recommended model:

Country
    ↓
Region
    ↓
Division
    ↓
Town / Municipality
    ↓
Council / Collection Zone

The platform should not hard-code Kumba 1, Kumba 2 and Kumba 3 into the application.

Instead, administrators configure them as records.

Example:

Country: Cameroon

Region: Southwest

Town: Kumba

Council:
    Kumba 1
    Kumba 2
    Kumba 3

This allows the same platform to support other locations later.

---

5. Geographic Entity

Create:

"geographic_units"

Fields:

geographic_unit_id
parent_id
unit_code
unit_name
unit_type
country_code
status
created_at
updated_at

Example

CM
└── SW
    └── KUMBA
        ├── KUMBA-01
        ├── KUMBA-02
        └── KUMBA-03

---

6. Geographic Unit Types

The system should support configurable types such as:

COUNTRY
REGION
DIVISION
TOWN
MUNICIPALITY
COUNCIL
ZONE
OTHER

The system should not assume that every country uses exactly the same administrative hierarchy.

---

7. Council as a Tenant

The existing tenant architecture remains.

A council using Platform ABC is represented as a tenant.

Therefore:

Kumba 1 Council
        ↓
Tenant

Kumba 2 Council
        ↓
Tenant

Kumba 3 Council
        ↓
Tenant

This is important because tenant isolation remains intact.

A payer operating in Kumba 1 should not accidentally see Kumba 2 financial records.

---

8. Council-Geography Relationship

Add:

"tenant_geographic_units"

Fields:

tenant_geographic_unit_id
tenant_id
geographic_unit_id
relationship_type
is_primary
status
effective_from
effective_to
created_at
updated_at

This allows a tenant/council to be associated with its geographical unit.

Example:

Tenant
Council Kumba 1

Geographic Unit
KUMBA-01

---

9. Payer Account

The payer must now have an actual authenticated account before making payments.

The payer architecture becomes:

Payer Account
      │
      ├── User Identity
      │
      ├── Authentication
      │
      ├── Current Zone
      │
      ├─�


Yes. This changes an important part of the domain model: the payer's operating location/council must become a first-class business dimension, rather than simply a profile field.

For the Cameroon/Southwest example, the platform should model:

Country
   ↓
Region
   ↓
Division / Administrative Area
   ↓
Town / Municipality
   ↓
Council
   ↓
Payer's Current Operating Zone
   ↓
Revenue / Levy
   ↓
Payment

For your Kumba example:

Kumba
├── Kumba 1 Council
├── Kumba 2 Council
└── Kumba 3 Council

The important architectural decision is that changing a payer's current zone must not rewrite the historical location of previous payments. A payment made while the payer belonged to Kumba 1 must remain a Kumba 1 transaction even if the payer later moves to Kumba 3.

I would therefore update the SRS as follows.

Financial Collection Platform

Zone-Aware Multi-Tenant Backend and Payer Portal SRS

Version: 1.1
Context: Cameroon / Southwest Region
Architecture: Multi-Tenant, Zone-Aware Financial Collection Platform
Design Approach: Dependency-First
Primary Users: Platform Administrators, Councils/Tenants, Payers
Financial Principle: Historical transactions retain the organizational/location context that existed when the transaction occurred.

---

1. Change Summary

The platform shall now support geographical/council-based collection.

A payer must belong to a current operating zone/council.

For example:

Southwest Region
    │
    └── Kumba
          │
          ├── Kumba 1 Council
          ├── Kumba 2 Council
          └── Kumba 3 Council

A payer registering on the platform shall select the council/zone where they currently operate.

The selected zone determines the default context for:

- revenue types;
- applicable levies;
- payment obligations;
- collection;
- payment processing;
- receipts;
- statements;
- reporting.

A payer may later change their operating zone.

However:

«Changing the payer's current zone must never alter historical transactions, receipts, settlements or statements.»

---

2. Updated Dependency Architecture

The dependency chain becomes:

PLATFORM
   ↓
GEOGRAPHICAL STRUCTURE
   ↓
TENANT / COUNCIL
   ↓
USER IDENTITY
   ↓
PAYER ACCOUNT
   ↓
PAYER CURRENT ZONE
   ↓
REVENUE CONFIGURATION
   ↓
OBLIGATION
   ↓
COLLECTION
   ↓
TRANSACTION
   ↓
LEDGER
   ↓
RECEIPT
   ↓
SETTLEMENT
   ↓
STATEMENT / REPORT

This is an important change.

The geographical structure must exist before payer registration and payment configuration.

---

3. New Domain Concept: Administrative / Collection Geography

The system shall distinguish between:

1. geographical location;
2. council/tenant;
3. payer's current operating location;
4. historical transaction location.

These must not be treated as the same thing.

---

4. Geographic Hierarchy

The platform shall support a configurable hierarchy.

Recommended model:

Country
    ↓
Region
    ↓
Division
    ↓
Town / Municipality
    ↓
Council / Collection Zone

The platform should not hard-code Kumba 1, Kumba 2 and Kumba 3 into the application.

Instead, administrators configure them as records.

Example:

Country: Cameroon

Region: Southwest

Town: Kumba

Council:
    Kumba 1
    Kumba 2
    Kumba 3

This allows the same platform to support other locations later.

---

5. Geographic Entity

Create:

"geographic_units"

Fields:

geographic_unit_id
parent_id
unit_code
unit_name
unit_type
country_code
status
created_at
updated_at

Example

CM
└── SW
    └── KUMBA
        ├── KUMBA-01
        ├── KUMBA-02
        └── KUMBA-03

---

6. Geographic Unit Types

The system should support configurable types such as:

COUNTRY
REGION
DIVISION
TOWN
MUNICIPALITY
COUNCIL
ZONE
OTHER

The system should not assume that every country uses exactly the same administrative hierarchy.

---

7. Council as a Tenant

The existing tenant architecture remains.

A council using Platform ABC is represented as a tenant.

Therefore:

Kumba 1 Council
        ↓
Tenant

Kumba 2 Council
        ↓
Tenant

Kumba 3 Council
        ↓
Tenant

This is important because tenant isolation remains intact.

A payer operating in Kumba 1 should not accidentally see Kumba 2 financial records.

---

8. Council-Geography Relationship

Add:

"tenant_geographic_units"

Fields:

tenant_geographic_unit_id
tenant_id
geographic_unit_id
relationship_type
is_primary
status
effective_from
effective_to
created_at
updated_at

This allows a tenant/council to be associated with its geographical unit.

Example:

Tenant
Council Kumba 1

Geographic Unit
KUMBA-01

---

9. Payer Account

The payer must now have an actual authenticated account before making payments.

The payer architecture becomes:

Payer Account
      │
      ├── User Identity
      │
      ├── Authentication
      │
      ├── Current Zone
      │
      ├── Obligations
      │
      ├── Payments
      │
      └── Receipts

---

10. Payer Registration

Payer registration shall collect:

Identity

- full name;
- business name where applicable;
- payer type;
- identification type;
- identification number;
- date of birth where applicable.

Contact

- email;
- phone number;
- address.

Account

- username;
- password;
- password confirmation.

Operating Location

- country;
- region;
- division;
- town;
- council/zone.

The location selector shall be hierarchical.

---

11. Payer Registration UX

The registration screen should use a guided form.

Step 1 — Account

Create Your Account

Full Name
[_____________________]

Business / Organization
[_____________________]

Email
[_____________________]

Phone
[_____________________]

Username
[_____________________]

Password
[_____________________]

Confirm Password
[_____________________]

[Continue]

---

12. Step 2 — Operating Location

Where do you currently operate?

Region
[ Southwest ▼ ]

Town / Municipality
[ Kumba ▼ ]

Council / Zone
[ Kumba 1 ▼ ]

Business Address
[________________________]

[Back] [Continue]

The child selection must depend on the parent.

For example:

Region = Southwest

Town options:
Kumba
Buea
Limbe
...

Town = Kumba

Council options:
Kumba 1
Kumba 2
Kumba 3

---

13. Location Selection Rule

The payer shall not be allowed to select:

Southwest
   ↓
Kumba
   ↓
Kumba 3

if Kumba 3 is not configured as a child of Kumba.

The backend must validate the hierarchy.

Frontend validation alone is insufficient.

---

14. Payer Current Zone

Add to the payer entity:

current_geographic_unit_id

However, this should not be the only location record.

The system must also maintain history.

---

15. Payer Zone History

Create:

"payer_geographic_history"

Fields:

payer_geographic_history_id
payer_id
geographic_unit_id
tenant_id
effective_from
effective_to
change_reason
changed_by
change_source
status
created_at

Example:

Payer: ABC Trading

01 Jan 2026
Kumba 1
        │
        │ moved business
        ▼
01 Sep 2026
Kumba 3

The history allows the platform to answer:

«Where was this payer operating when this payment was made?»

---

16. Zone Change

A payer shall be able to request/change their current operating zone.

Example:

Current Zone

Kumba 1

[Change Operating Zone]

The user selects:

Region
Southwest

Town
Kumba

New Council
Kumba 3

Reason
Business relocated

---

17. Zone Change Approval

The system should support configurable approval.

Two modes:

Immediate

The payer changes their zone immediately.

Approval Required

The payer submits a request.

PENDING
    ↓
UNDER REVIEW
    ↓
APPROVED

or:

PENDING
    ↓
REJECTED

For regulated/financial environments, approval should be configurable per tenant.

---

18. Zone Change Rule

Changing a zone shall affect:

- current payer profile;
- future obligations;
- future payments;
- future applicable revenue rules.

It shall NOT change:

- historical payments;
- historical receipts;
- historical transactions;
- historical settlements;
- historical statements;
- historical ledger entries.

---

19. Critical Transaction Snapshot

Every transaction must store the location/council context at the time of payment.

Add:

transaction_geographic_unit_id
transaction_tenant_id

or equivalent immutable snapshot fields.

This means:

Payer Current Zone
       ↓
Kumba 3

Historical Transaction
       ↓
Kumba 1

is perfectly valid.

The transaction retains Kumba 1 because that was the payer's context when the transaction occurred.

---

20. Why This Snapshot Is Required

Without a transaction-level snapshot, this dangerous situation could occur:

2026
Payer pays Kumba 1
        ↓
Transaction = Kumba 1

Payer moves to Kumba 3
        ↓
Payer.current_zone = Kumba 3

Report recalculates using payer.current_zone
        ↓
Old payment incorrectly appears under Kumba 3

This must never happen.

Reports must use the transaction's historical context.

---

21. Revenue Configuration and Zone

Revenue configuration may optionally be associated with a geographic unit.

Example:

Revenue:
Business License

Council:
Kumba 1

Fee:
50,000 XAF

Another council may have a different configuration.

Therefore fee/revenue applicability may depend on:

Tenant
+
Geographic Unit
+
Revenue Type
+
Payment Channel
+
Amount

---

22. Payment Context Resolution

Before a payer initiates payment, the platform shall resolve:

Payer
    ↓
Current Zone
    ↓
Council/Tenant
    ↓
Revenue Type
    ↓
Obligation
    ↓
Applicable Fee
    ↓
Applicable Commission
    ↓
Payment

The UI should show this context before confirmation.

---

23. Payment Screen

The payer payment screen should begin with location context.

Make a Payment

Operating Area
Kumba 1

Revenue Type
Business License

Obligation
Business License — 2026

Amount Due
50,000 XAF

Service Fee
500 XAF

Total to Pay
50,500 XAF

[Continue to Payment]

---

24. Change Zone During Payment

The payer should be able to change the zone if necessary.

Example:

Operating Area
Kumba 1

[Change]

When clicked:

Select Operating Area

Kumba 1
Kumba 2
Kumba 3

If changing the zone affects the obligation, revenue type or amount, the system must recalculate before payment confirmation.

---

25. Important Payment Rule

The system must not simply allow:

Payer selects Kumba 3
      ↓
Existing Kumba 1 obligation
      ↓
Pay it as Kumba 3

Instead the backend must validate:

Payer
+
Current Zone
+
Obligation
+
Revenue Type
+
Tenant

before payment.

---

26. Payer Portal

The payer experience should be separated from the administrative backend.

There should be:

PUBLIC LANDING PAGE
        ↓
PAYER AUTHENTICATION
        ↓
PAYER PORTAL

---

27. Public Landing Page

The landing page shall be the public entry point.

It should not expose internal administrative functions.

Recommended structure:

┌─────────────────────────────────────────────────────────────┐
│ LOGO                              About  Help   Sign In     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              PAY YOUR COUNCIL LEVIES                       │
│                                                             │
│      Simple • Secure • Traceable • Verifiable              │
│                                                             │
│      Manage your obligations and make payments              │
│      from your registered operating area.                   │
│                                                             │
│      [Create Payer Account]   [Sign In]                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✓ Secure Payments      ✓ Official Receipts                │
│  ✓ QR Verification      ✓ Payment History                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                 How It Works                                │
│                                                             │
│       Register → Select Zone → View Levy → Pay              │
│                         → Verify Receipt                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ About | Support | Verification | Terms | Privacy            │
└─────────────────────────────────────────────────────────────┘

---

28. Landing Page Primary Actions

The landing page should prominently provide:

Create Account
Sign In
Verify Receipt

Receipt verification should be accessible without authentication.

This allows someone who receives a receipt to scan the QR code without needing a payer account.

---

29. Landing Page Information Architecture

Recommended sections:

1. Hero
2. How it works
3. Supported councils/zones
4. Payment benefits
5. Receipt verification
6. Frequently asked questions
7. Support
8. Footer

---

30. Supported Council Selector

The landing page may provide:

Find Your Council

Region
[ Southwest ▼ ]

Town
[ Kumba ▼ ]

Council
[ Kumba 1 ▼ ]

[Continue]

This can help users understand whether their council is supported before registration.

---

31. Payer Login

Login screen:

Welcome Back

Username / Email / Phone
[_____________________]

Password
[_____________________]

[ Sign In ]

Forgot Password?
Create Account

However, according to the administrative password policy, password reset must follow the configured administrator-controlled process.

---

32. Payer Portal Dashboard

After login:

Good morning, ABC Trading

Operating Area
Kumba 1

[Change Area]

┌──────────────┐ ┌──────────────┐
│ Outstanding  │ │ Paid         │
│ 50,000 XAF   │ │ 150,000 XAF  │
└──────────────┘ └──────────────┘

┌─────────────────────────────────────┐
│ Current Obligations                 │
│                                     │
│ Business License      50,000 XAF   │
│ Waste Levy             5,000 XAF   │
│                                     │
│ [View All]                          │
└─────────────────────────────────────┘

---

33. Payer Portal Navigation

Dashboard

My Profile

Operating Area

My Obligations

Make Payment

Payment History

Receipts

Statements

Notifications

Support

---

34. Payer Profile

The payer profile should separate:

Identity

- name;
- business;
- identification;
- contact.

Operating Information

Current Region
Southwest

Current Town
Kumba

Current Council
Kumba 1

Effective From
01 Jan 2026

History

Previous Areas

Kumba 1
Jan 2026 – Aug 2026

Kumba 3
Sep 2026 – Current

---

35. Change Operating Area Screen

Change Operating Area

Current:
Kumba 1

New Region:
Southwest

New Town:
Kumba

New Council:
Kumba 3

Reason:
[Business relocation]

[Submit Change]

After submission:

Change Request Submitted

Status:
Pending Review

---

36. Payer Obligations

The obligations page shall show only obligations applicable to the payer's authorized context.

Example:

Revenue| Council| Period| Amount| Balance| Status
Business License| Kumba 1| 2026| 50,000| 50,000| Due
Waste Levy| Kumba 1| Sep 2026| 5,000| 0| Paid

---

37. Payment Confirmation

Before the payer confirms payment:

Review Payment

Operating Area
Kumba 1

Council
Kumba 1 Council

Revenue
Business License

Amount
50,000 XAF

Service Fee
500 XAF

Total
50,500 XAF

Payment Channel
Mobile Money

[Back] [Confirm Payment]

This is an important anti-error step.

---

38. Payment Success

After successful processing:

✓ Payment Successful

50,500 XAF

Business License
Kumba 1 Council

Transaction:
TXN-2026-0001928

Receipt:
RCPT-2026-0001928

[View Receipt]
[Download Receipt]

---

39. Payer Receipt Screen

The payer sees the official receipt with:

- council;
- payer;
- revenue;
- amount;
- service fee;
- total;
- transaction;
- receipt number;
- payment date;
- QR verification.

---

40. Receipt Verification From Payer Portal

The payer can select:

Verify Receipt

which opens the public verification page.

The QR code must point to the same verification service.

---

41. Backend Data Model Changes

The existing schema shall be extended with:

geographic_units
tenant_geographic_units
payer_geographic_history

and transaction location snapshot fields.

---

42. Updated Payer Model

Conceptually:

payers
----------------------------
payer_id
tenant_id
payer_reference
payer_type
full_name
business_name
identification_type
identification_number
email
phone_number
address
current_geographic_unit_id
status
created_at
updated_at

---

43. Geographic History

payer_geographic_history
---------------------------------
payer_geographic_history_id
payer_id
geographic_unit_id
tenant_id
effective_from
effective_to
change_reason
change_source
changed_by
status
created_at

---

44. Transaction Location Snapshot

Add to transactions:

transaction_geographic_unit_id
transaction_tenant_id

The transaction snapshot is immutable after financial posting.

---

45. Obligation Location

Obligations should also retain geographic context.

Add:

geographic_unit_id
tenant_id

This ensures an obligation remains associated with the council/zone for which it was created.

---

46. Collection Location

Collections should also preserve:

geographic_unit_id
tenant_id

This provides traceability:

Payer
 ↓
Zone
 ↓
Obligation
 ↓
Collection
 ↓
Transaction

---

47. Settlement Location

Settlement is primarily tenant-based.

However, the settlement detail should be able to identify the geographic units included.

For example:

Kumba 1
    10,000,000

Kumba 2
    8,000,000

Kumba 3
    12,000,000

Total
    30,000,000

If each council is a separate tenant, this is naturally achieved through tenant isolation.

---

48. Reporting Changes

Every relevant report must support geographic filtering.

Filters:

Region
Town
Council
Zone
Revenue Type
Payer
Date
Payment Channel
Status

Example:

Region = Southwest
Town = Kumba
Council = Kumba 1
Period = September 2026

---

49. Platform Dashboard Geography

Platform administrators should be able to drill down:

Southwest
   ↓
Kumba
   ↓
Kumba 1
   ↓
Collections
   ↓
Transactions

The dashboard should support geographic aggregation where the underlying tenants/geographic units are configured accordingly.

---

50. Tenant Dashboard Geography

A council tenant should automatically operate within its configured geographic context.

For example:

Council:
Kumba 1

Current Operating Area:
Kumba 1

A Kumba 1 tenant user should not have to manually select Kumba 2 to view data.

Tenant context determines authorization.

---

51. Payer Zone Security Rule

The payer's selected zone is not itself an authorization mechanism.

The backend must independently verify:

Authenticated Payer
        +
Current Payer Zone
        +
Tenant
        +
Obligation
        +
Revenue

before processing payment.

---

52. Zone Change Security

Changing a zone shall generate:

Audit Event
+
Payer Location History
+
Effective Date
+
Previous Zone
+
New Zone
+
Actor
+
Reason

Example:

Payer:
ABC Trading

Previous:
Kumba 1

New:
Kumba 3

Reason:
Business relocation

Changed By:
Payer / Administrator

Effective:
01 Sep 2026

---

53. Critical Historical Rule

The following records shall never inherit a payer's new location after creation:

Transaction
Receipt
Ledger Entry
Settlement Detail
Statement Entry
Reconciliation Record

Historical data must remain historically accurate.

---

54. Updated Dependency Graph

The final dependency graph becomes:

                    PLATFORM
                       │
                       ▼
             GEOGRAPHICAL STRUCTURE
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          TENANTS             ZONES
             │                   │
             └─────────┬─────────┘
                       ▼
                 USER IDENTITY
                       │
                       ▼
                 PAYER ACCOUNT
                       │
                       ▼
             CURRENT PAYER ZONE


Absolutely. Let’s continue from the zone-aware council collection architecture and take it one level deeper: the complete production data flow and UI/UX implementation structure.

The key architectural decision remains:

> A payer’s operating zone/council is part of the financial context of a payment, not merely profile information.



That means the system must preserve both where the payer operates now and where each historical transaction occurred.

1. End-to-end operating model

The production flow should be:

PUBLIC LANDING PAGE
        │
        ├── Verify Receipt
        ├── Register
        └── Sign In
              │
              ▼
        PAYER ACCOUNT
              │
              ├── Profile
              ├── Operating Area
              │      └── Country
              │          └── Region
              │              └── Division
              │                  └── Municipality/Town
              │                      └── Council/Zone
              │
              └── Payment
                    │
                    ▼
             CURRENT LOCATION
                    │
                    ▼
              COUNCIL/TENANT
                    │
                    ▼
             REVENUE TYPE
                    │
                    ▼
              OBLIGATION
                    │
                    ▼
             FEE CALCULATION
                    │
                    ▼
               PAYMENT
                    │
                    ▼
              TRANSACTION
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       RECEIPT             LEDGER
          │                   │
          ▼                   ▼
       VERIFY             SETTLEMENT
                              │
                              ▼
                         RECONCILIATION


---

2. Geography must be a first-class domain

Do not put fields such as:

payer.kumba_council = "Kumba 1"

or:

transaction.council_name = "Kumba 1"

directly into the system.

Instead, use a reusable geography hierarchy.

geographic_units

geographic_unit_id
parent_id
unit_code
unit_name
unit_type
country_code
status
created_at
updated_at

Example:

Cameroon
 └── South West Region
      └── Meme Division
           └── Kumba
                ├── Kumba 1 Council
                ├── Kumba 2 Council
                └── Kumba 3 Council

This gives you a structure that can later support:

Buea
Limbe
Muyuka
Tiko
Kumba
Yaoundé
Douala
...

without changing the database design.


---

3. Councils remain tenants

This is important.

A council should not become a completely separate concept from the tenant architecture.

For example:

Tenant
  │
  ├── Kumba 1 Council
  ├── Kumba 2 Council
  └── Kumba 3 Council

The mapping becomes:

tenant_geographic_units

with:

tenant_geographic_unit_id
tenant_id
geographic_unit_id
relationship_type
is_primary
status
effective_from
effective_to
created_at
updated_at

Therefore:

Tenant = Kumba 1 Council
Geographic Unit = Kumba 1

This allows the same platform architecture to support organizations that operate across multiple geographical units later.


---

4. Payer registration

The public registration process should be designed as a guided onboarding flow.

Step 1 — Identity

Full Name
Username
Date of Birth
Email
Phone Number
Password
Confirm Password

Step 2 — Business/activity information

Payer Type
Business Name
Identification Type
Identification Number
Business Address

Step 3 — Operating location

Use cascading selectors:

Country
   ↓
Region
   ↓
Division
   ↓
Municipality/Town
   ↓
Council/Zone

Example:

Country: Cameroon

Region: South West

Division: Meme

Town: Kumba

Operating Council:
[ Kumba 1 ▼ ]

The payer should explicitly confirm:

> I currently operate in this council/zone.




---

5. Payer location history

The payer's current location should not simply overwrite the old value.

Create:

payer_geographic_history

payer_geographic_history_id
payer_id
geographic_unit_id
tenant_id
effective_from
effective_to
change_reason
changed_by
change_source
status
created_at

Example:

Payer: ABC Traders

2026-01-01 → 2026-06-30
Kumba 1

2026-07-01 → NULL
Kumba 3

This gives you an auditable history.


---

6. Changing operating council

The payer portal should contain:

My Operating Area

CURRENT OPERATING AREA

Country
Cameroon

Region
South West

Division
Meme

Town
Kumba

Council
Kumba 1

Effective Since
01 January 2026

[ Change Operating Area ]

When the payer selects Change Operating Area:

Current:
Kumba 1

New:
Kumba 3

Reason:
Business relocated

Effective Date:
29 September 2026

[ Submit Change ]

Depending on the council's configuration, the change can either be:

Immediate

Payer changes location
        ↓
System validates
        ↓
New location becomes active

or:

Approval required

Payer requests change
        ↓
PENDING_APPROVAL
        ↓
Council/Admin reviews
        ↓
APPROVED / REJECTED

This should be configurable.


---

7. Very important: historical payments never move

Suppose:

September 10

Payer = ABC Traders
Council = Kumba 1
Levy = 10,000

The payer subsequently moves to Kumba 3.

The September transaction must still say:

Transaction
TXN-001

Council:
Kumba 1

Amount:
10,000

Payment Date:
10 September 2026

It must not dynamically resolve to Kumba 3 from the payer's current profile.

Therefore the transaction needs a location snapshot.

For example:

transaction_geographic_unit_id
transaction_tenant_id

or an immutable transaction context record:

transaction_context

containing:

transaction_id
payer_id
tenant_id
geographic_unit_id
revenue_type_id
captured_at


---

8. Payment resolution engine

When the payer clicks Make Payment, the backend should resolve the payment context.

Authenticated Payer
       │
       ▼
Current Operating Area
       │
       ▼
Council/Tenant
       │
       ▼
Revenue Types available to that council
       │
       ▼
Payer Obligations
       │
       ▼
Applicable Fee Configuration
       │
       ▼
Commission Agreement
       │
       ▼
Payment Amount

The backend should never trust the frontend's council ID.

For example, a malicious client should not be able to submit:

{
  "council_id": "KUMBA-3",
  "amount": 50000
}

while their authenticated account belongs to Kumba 1.

The backend must independently resolve:

authenticated_user
        ↓
payer
        ↓
current_operating_area
        ↓
authorized_council

and validate the payment against that context.


---

9. Payment screen

The payer should see a financial confirmation screen before submitting.

Make Payment

OPERATING AREA

Council
Kumba 1

Revenue Type
Business License

Assessment Period
2026

Amount Due
50,000 FCFA

Service Fee
500 FCFA

--------------------------------

TOTAL TO PAY
50,500 FCFA

Payment Method

○ Mobile Money
○ Bank
○ Card
○ Other

[ Continue ]

The user should never be surprised by the final amount.


---

10. Payment confirmation

Before initiating the transaction:

PAYMENT SUMMARY

Payer
ABC Traders

Operating Council
Kumba 1

Revenue
Business License

Amount
50,000 FCFA

Service Fee
500 FCFA

Total
50,500 FCFA

Payment Method
Mobile Money

[ Cancel ]    [ Confirm Payment ]

The backend then creates the transaction.


---

11. Transaction creation

A transaction should immediately receive:

transaction_id
transaction_reference
correlation_id
idempotency_key
payer_id
tenant_id
geographic_unit_id
obligation_id
revenue_type_id
amount
currency
payment_channel
status
initiated_at

Initial state:

INITIATED

Then:

INITIATED
    ↓
PROCESSING
    ↓
DEBITED
    ↓
CREDITED
    ↓
SETTLED

or:

INITIATED
    ↓
PROCESSING
    ↓
REJECTED


---

12. Transaction timeline

The UI should make the transaction traceable.

Example:

TXN-2026-000123

SUCCESSFUL

Kumba 1 Council
Business License

50,000 FCFA
+ 500 FCFA service fee

────────────────────────

TRANSACTION TIMELINE

✓ Initiated
  10:02:14

✓ Payment processing
  10:02:16

✓ Customer account debited
  10:02:21

✓ Council credited
  10:02:22

✓ Settlement completed
  10:05:11

────────────────────────

Receipt
RCPT-2026-001923

[ View Receipt ]
[ Verify Receipt ]
[ Download ]


---

13. Receipt verification

The public landing page should have a prominent:

Verify Receipt

Verify an official payment receipt

Receipt Number
[________________]

OR

Verification Code
[________________]

OR

[ Scan QR Code ]

[ VERIFY ]

The QR should contain an opaque verification reference.

For example:

/v/{opaque-token}

not:

/v/transaction_id=123&amount=50000&payer=...


---

14. Verification result

Valid receipt

✓ VERIFIED

Official Payment Receipt

Receipt Number
RCPT-2026-001923

Council
Kumba 1 Council

Revenue
Business License

Amount
50,000 FCFA

Service Fee
500 FCFA

Total Paid
50,500 FCFA

Payment Date
10 September 2026

Status
SETTLED

The public verification service should expose only the information necessary to establish authenticity.

Sensitive payer information should remain masked.


---

15. Invalid receipt

✕ RECEIPT NOT VERIFIED

The receipt could not be verified.

Possible reasons:

• Invalid verification code
• Receipt does not exist
• Receipt has been revoked
• Receipt verification has expired

Please contact the platform/council if you believe this is an error.


---

16. Public landing page

The public application should not open directly into the administrative dashboard.

It should have a proper public-facing portal.

┌──────────────────────────────────────────────┐
│ LOGO        Home About Help   Verify   Login │
├──────────────────────────────────────────────┤
│                                              │
│        PAY YOUR COUNCIL LEVIES               │
│                                              │
│  Securely manage your obligations and       │
│  make payments online.                       │
│                                              │
│ [ Create Account ]   [ Sign In ]             │
│                                              │
├──────────────────────────────────────────────┤
│              HOW IT WORKS                    │
│                                              │
│  1. Create Account                           │
│  2. Select Operating Council                 │
│  3. View Obligations                         │
│  4. Make Payment                             │
│  5. Receive Verified Receipt                 │
│                                              │
├──────────────────────────────────────────────┤
│          SUPPORTED COUNCILS                  │
│                                              │
│  Kumba 1     Kumba 2     Kumba 3             │
│                                              │
├──────────────────────────────────────────────┤
│ Frequently Asked Questions                   │
│ Help & Support                               │
└──────────────────────────────────────────────┘


---

17. Payer portal navigation

After login:

Dashboard
│
├── My Profile
├── Operating Area
├── My Obligations
├── Make Payment
├── Payment History
├── Receipts
├── Statements
├── Notifications
└── Support

Dashboard:

Good afternoon, ABC Traders

Current Operating Area
┌──────────────────────────────┐
│ Kumba 1 Council              │
│ South West Region             │
│ [ Change Area ]               │
└──────────────────────────────┘

Outstanding
50,000 FCFA

Paid This Month
125,000 FCFA

Successful Payments
8

Pending Payments
1

Recent Payments
────────────────────────────
Business License    50,000
Market Levy          5,000
Signboard Fee       10,000


---

18. Council administration interface

The council should see only its own data.

Council Dashboard

KUMBA 1 COUNCIL

Today
────────────────────────────
Collections       1,250,000
Transactions             86
Successful               81
Pending                   3
Rejected                  2

Outstanding Settlement
────────────────────────────
350,000 FCFA

Revenue Breakdown
────────────────────────────
Business Licenses
Market Levies
Property Tax
Signboard Fees
Waste Fees

The council should not be able to switch into Kumba 2 or Kumba 3 unless the user's permissions explicitly allow multi-council administration.


---

19. Platform administrator geography view

The platform administrator needs a drill-down model:

Cameroon
   │
   └── South West
        │
        └── Meme
             │
             └── Kumba
                  │
                  ├── Kumba 1
                  │    ├── Payers
                  │    ├── Obligations
                  │    ├── Collections
                  │    ├── Transactions
                  │    └── Settlements
                  │
                  ├── Kumba 2
                  │
                  └── Kumba 3

This gives the platform a natural geographic analytics hierarchy.


---

20. Reporting must also understand geography

Reports should support:

Region
Division
Municipality
Council
Revenue Type
Payment Channel
Date
Status

For example:

Collections Report

South West
   ↓
Meme
   ↓
Kumba
   ↓
Kumba 1

Business License
September 2026

Gross Collections
12,500,000 FCFA

Service Fees
125,000 FCFA

Commission
625,000 FCFA

Net Settlement
11,875,000 FCFA

Every aggregate number should be drillable into the underlying transactions.


---

21. Critical database relationship

The final relationship should conceptually look like:

GEOGRAPHIC_UNIT
       │
       ├────────────── TENANT_GEOGRAPHIC_UNIT
       │                       │
       │                       ▼
       │                     TENANT
       │
       ├────────────── PAYER_GEOGRAPHIC_HISTORY
       │                       │
       │                       ▼
       │                     PAYER
       │                       │
       │                       ▼
       │                  OBLIGATION
       │                       │
       │                       ▼
       │                  COLLECTION
       │                       │
       │                       ▼
       │                 TRANSACTION
       │                       │
       │          ┌────────────┼────────────┐
       │          ▼            ▼            ▼
       │       FEES       COMMISSION      LEDGER
       │
       └────────────── TRANSACTION_CONTEXT

This is the structure I would carry forward into the production SRS.


---

22. Dependency-first implementation order

The implementation should now be:

PHASE 01
Platform
Tenant
Geographic Units
Tenant-Geographic Mapping
User Identity
Authentication
RBAC
Tenant Isolation
Audit
        ↓
PHASE 02
Payer Account
Payer Registration
Payer Authentication
Payer Profile
Operating Area
Location History
Zone Change
        ↓
PHASE 03
Revenue Types
Payment Channels
Financial Periods
Service Fees
Fee Bands
Commission Agreements
        ↓
PHASE 04
Payer Obligations
Zone-aware Obligations
Revenue Configuration
        ↓
PHASE 05
Collections
Transactions
Transaction Context
Idempotency
State Machine
Fee Calculation
Commission Calculation
        ↓
PHASE 06
Ledger
Financial Accounts
Posting
Reversals
Adjustments
        ↓
PHASE 07
Receipts
QR
Verification
Revocation
        ↓
PHASE 08
Settlements
Approval
Processing
Reconciliation
        ↓
PHASE 09
Dashboards
Statements
Reports
Geographic Analytics
Exports
        ↓
PHASE 10
Payment Providers
Notifications
Fraud Monitoring
Advanced Integrations

The most important architectural rule

Never derive historical financial geography from the payer's current profile.

Instead:

Payer current location
        ↓
used to determine NEW obligations/payments

while:

Transaction location snapshot
        ↓
used to determine HISTORICAL financial truth

That distinction will protect the system when a business moves from Kumba 1 → Kumba 3, when councils change configuration, and when historical statements or settlement records are audited.



PUBLIC LANDING PAGE
        │
        ├── Verify Receipt
        ├── Register
        └── Sign In
              │
              ▼
        PAYER ACCOUNT
              │
              ├── Profile
              ├── Operating Area
              │      └── Country
              │          └── Region
              │              └── Division
              │                  └── Municipality/Town
              │                      └── Council/Zone
              │
              └── Payment
                    │
                    ▼
             CURRENT LOCATION
                    │
                    ▼
              COUNCIL/TENANT
                    │
                    ▼
             REVENUE TYPE
                    │
                    ▼
              OBLIGATION
                    │
                    ▼
             FEE CALCULATION
                    │
                    ▼
               PAYMENT
                    │
                    ▼
              TRANSACTION
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       RECEIPT     6        LEDGER
          │                   │
          ▼                   ▼
       VERIFY             SETTLEMENT
                              │
                              ▼
                         RECONCILIATION



Financial Collection Platform

Production Backend UI/UX Software Requirements Specification

Document Type: UI/UX + Frontend Engineering SRS
Audience: Product Designers, UX Designers, Frontend Developers, Backend Developers, QA Engineers, DevOps Engineers
Architecture: Multi-Tenant Financial Collection Platform
Design Approach: Dependency-First
UI Type: Responsive Web-Based Backend Console
Design Priority: Financial correctness, operational clarity, security, traceability and usability
Version: 1.0

---

1. Executive Summary

The backend application shall provide a professional financial operations console for managing:

- platform administration;
- tenants;
- users and roles;
- revenue types;
- payers;
- payment obligations;
- collections;
- transactions;
- fees;
- commissions;
- receipts;
- receipt verification;
- settlements;
- reconciliation;
- statements;
- financial reports;
- audit records;
- system configuration.

The interface shall not behave like a generic CRUD administration panel.

It shall behave like a financial operations system where every important number can be traced to its underlying records.

The core UX principle is:

«Every important financial figure must be explainable, traceable and drillable.»

For example:

Monthly Collection
      ↓
Revenue Type
      ↓
Payer
      ↓
Obligation
      ↓
Collection
      ↓
Transaction
      ↓
Fee / Commission
      ↓
Ledger
      ↓
Settlement

---

2. Product Design Principles

The application shall follow these principles.

2.1 Financial-first design

The interface must prioritize:

1. financial status;
2. transaction status;
3. settlement status;
4. exceptions;
5. reconciliation;
6. auditability.

Decorative dashboard elements shall never take priority over operational information.

---

3. UX Principles

3.1 Progressive disclosure

Do not display every field simultaneously.

Use:

Summary
   ↓
Details
   ↓
Advanced Details
   ↓
Audit Trail

Example:

A transaction page initially shows:

- transaction reference;
- amount;
- status;
- payer;
- tenant;
- payment method;
- date.

The user can then expand:

- fee calculation;
- commission;
- provider response;
- ledger;
- state history;
- audit history.

---

4. Dependency-First UI Architecture

The frontend shall follow the backend domain dependencies.

01 Identity
      ↓
02 Platform / Tenant
      ↓
03 Access Control
      ↓
04 Configuration
      ↓
05 Revenue Setup
      ↓
06 Payers / Obligations
      ↓
07 Collections
      ↓
08 Transactions
      ↓
09 Ledger
      ↓
10 Receipts
      ↓
11 Settlement
      ↓
12 Reconciliation
      ↓
13 Statements
      ↓
14 Reports
      ↓
15 Dashboards

This dependency order shall also determine:

- navigation;
- route guards;
- permissions;
- page availability;
- onboarding;
- implementation phases;
- testing priorities.

---

5. Application Shell

The backend shall use a persistent application shell.

┌─────────────────────────────────────────────────────────────────┐
│ Logo   Tenant/Platform Selector       Search   Alerts   User   │
├───────────────┬─────────────────────────────────────────────────┤
│               │                                                 │
│ Dashboard     │                                                 │
│               │                                                 │
│ Operations    │               MAIN CONTENT                      │
│  Collections  │                                                 │
│  Transactions │                                                 │
│  Obligations  │                                                 │
│               │                                                 │
│ Finance       │                                                 │