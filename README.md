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
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

### Docker Compose

```bash
docker compose up --build
```

## Demo accounts (after seed)

| User | Password | Role |
|------|----------|------|
| `admin` | `admin123` | Platform admin |
| `kumba1_admin` | `council123` | Kumba 1 council admin |
| `abctrading` | `payer123` | Payer in Kumba 1 |

## Architecture highlights

- Dependency-first modules (geography before payers, transactions before settlements)
- Shared MySQL DB with tenant isolation
- Immutable transaction geographic/tenant snapshots
- Payer zone history; zone changes never rewrite historical payments
- Double-entry ledger postings on settlement
- Public opaque-token receipt verification
- Portals: public landing, payer, council admin, platform admin

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) and [EasyPay SRS.md](./EasyPay%20SRS.md).
