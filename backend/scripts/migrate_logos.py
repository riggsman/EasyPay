"""Apply additive schema changes for tenant/platform logos (idempotent)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.services.branding import ensure_default_platform_logo, ensure_logo_schema


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_logo_schema(db)
        path = ensure_default_platform_logo(db)
        print("OK: logo columns ensured")
        print("OK: default platform logo →", path)
    finally:
        db.close()
    print("Migration complete")


if __name__ == "__main__":
    main()
