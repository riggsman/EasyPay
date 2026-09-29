"""Apply additive schema changes for Campay / provider encryption (idempotent)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.models import Base
from app.db.session import SessionLocal, engine


ALTERS = [
    "ALTER TABLE transactions ADD COLUMN payment_provider VARCHAR(64) NULL",
    "ALTER TABLE transactions ADD COLUMN provider_reference VARCHAR(128) NULL",
    "ALTER TABLE transactions ADD COLUMN provider_status VARCHAR(32) NULL",
    "ALTER TABLE transactions ADD COLUMN payer_msisdn VARCHAR(32) NULL",
    "ALTER TABLE settlements ADD COLUMN payout_method VARCHAR(32) NULL",
    "ALTER TABLE settlements ADD COLUMN payout_destination VARCHAR(128) NULL",
    "ALTER TABLE settlements ADD COLUMN payout_provider_reference VARCHAR(128) NULL",
    "ALTER TABLE settlements ADD COLUMN payout_status VARCHAR(32) NULL",
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
