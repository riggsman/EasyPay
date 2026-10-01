"""Additive schema for utility services / bill-pay (idempotent)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.services.utilities import ensure_sample_utility_services


ALTERS = [
    "ALTER TABLE transactions ADD COLUMN product_type VARCHAR(32) NOT NULL DEFAULT 'LEVY'",
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
        try:
            db.execute(text("CREATE INDEX ix_transactions_product_type ON transactions (product_type)"))
            db.commit()
            print("OK: index product_type")
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print("SKIP: index ->", str(exc).split("\n")[0][:120])
        seeded = ensure_sample_utility_services(db)
        print("OK: sample services", seeded)
    finally:
        db.close()
    print("Migration complete")


if __name__ == "__main__":
    main()
