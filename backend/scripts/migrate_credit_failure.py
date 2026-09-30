"""Additive schema for council-credit failure, retries, and manual intervention."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.models import Base
from app.db.session import SessionLocal, engine


ALTERS = [
    "ALTER TABLE transactions ADD COLUMN failure_reason TEXT NULL",
    "ALTER TABLE transactions ADD COLUMN failure_stage VARCHAR(32) NULL",
    "ALTER TABLE transactions ADD COLUMN credit_retry_count INT NOT NULL DEFAULT 0",
    "ALTER TABLE transactions ADD COLUMN credit_destination VARCHAR(128) NULL",
    "ALTER TABLE transactions ADD COLUMN credit_payout_method VARCHAR(32) NULL",
    "ALTER TABLE transactions ADD COLUMN credit_provider_reference VARCHAR(128) NULL",
    "ALTER TABLE transactions ADD COLUMN manual_intervention_at DATETIME NULL",
    "ALTER TABLE transactions ADD COLUMN manual_intervention_by VARCHAR(36) NULL",
    "ALTER TABLE tenants ADD COLUMN momo_number VARCHAR(64) NULL",
    "ALTER TABLE tenants ADD COLUMN bank_account_number VARCHAR(128) NULL",
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for stmt in ALTERS:
            try:
                db.execute(text(stmt))
                db.commit()
                print("OK:", stmt)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                print("SKIP:", stmt, "->", str(exc).split("\n")[0][:120])
    finally:
        db.close()
    print("Migration complete")


if __name__ == "__main__":
    main()
