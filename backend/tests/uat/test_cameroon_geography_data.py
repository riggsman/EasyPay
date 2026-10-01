"""Cameroon geography data file shape used by populate_cameroon_geography."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "cameroon_geography.json"


def test_cameroon_geography_json_counts_and_types():
    tree = json.loads(DATA.read_text(encoding="utf-8"))
    assert tree["unit_code"] == "CM"
    assert tree["unit_type"] == "COUNTRY"
    meta = tree["_meta"]["counts"]
    assert meta["regions"] == 10
    assert meta["divisions"] == 58
    assert meta["councils"] == 360

    regions = tree["children"]
    assert len(regions) == 10
    assert {r["unit_type"] for r in regions} == {"REGION"}
    assert any(r["unit_code"] == "CM-SW" and r["unit_name"] == "Southwest" for r in regions)

    divisions = [d for r in regions for d in r["children"]]
    assert len(divisions) == 58
    assert {d["unit_type"] for d in divisions} == {"DIVISION"}

    councils = [c for d in divisions for c in d["children"]]
    assert len(councils) == 360
    assert {c["unit_type"] for c in councils} == {"COUNCIL"}

    kumba = next(c for c in councils if c["unit_code"] == "CM-SW-MEME-KUMBA-1")
    assert kumba["unit_name"] == "Kumba 1"
    assert "KUMBA-01" in kumba["aliases"]


def test_populate_script_is_idempotent(client):  # noqa: ARG001 — ensures DB fixtures exist
    from scripts.populate_cameroon_geography import populate
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        first = populate(db, dry_run=False, prune=False)
        second = populate(db, dry_run=False, prune=False)
    finally:
        db.close()

    assert first["created"] + first["updated"] + first["unchanged"] == 429
    assert second["created"] == 0
    assert second["unchanged"] == 429
