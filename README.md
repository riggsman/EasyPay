# EasyPay

Zone-aware multi-tenant financial collection platform for council levies and revenue.

**Stack:** FastAPI · MySQL · React (JSX)

## Quick start (local)

### 1. Database

MariaDB/MySQL with database `easypay` and user `easypay` / `easypay`.

```bash
# Example
sudo mysql -e "CREATE DATABASE easypay CHARACTER SET utf8mb4; CREATE USER 'easypay'@'localhost' IDENTIFIED BY 'easypay'; GRANT ALL ON easypay.* TO 'easypay'@'localhost';"
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed.py
uvicorn app.main:asgi_app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:3000

### Docker Compose

```bash
docker compose up --build
```

## Demo accounts (after seed)

```bash
cd backend && python scripts/seed.py
```

| User | Password | Role |
|------|----------|------|
| `admin` (`wireitapp@gmail.com` / `682835503`) | `admin123` | Super admin |
| `kumba1_admin` / `kumba2_admin` / `kumba3_admin` | `council123` | Council admins |
| `abctrading` | `payer123` | Payer in Kumba 1 (Business License DUE, Waste Levy PAID) |
| `mambagroceries` | `payer123` | Payer in Kumba 1 (Market Levy + Signboard PAID) |
| `buearoasters` | `payer123` | Payer in Kumba 2 (Business License + Waste Levy PAID) |
| `threeconner` | `payer123` | Payer in Kumba 3 (Market Levy PAID) |

Seed is idempotent: re-running ensures providers (Campay mock, Email, WhatsApp, SMS), notification toggles, sample payers, and settled MoMo payments without duplicating foundation data.

## Architecture highlights

- Dependency-first modules (geography before payers, transactions before settlements)
- Shared MySQL DB with tenant isolation
- Immutable transaction geographic/tenant snapshots
- Payer zone history; zone changes never rewrite historical payments
- Double-entry ledger postings on settlement
- Public opaque-token receipt verification
- Portals: public landing, payer, council admin, platform admin

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) and [EasyPay SRS.md](./EasyPay%20SRS.md).
