"""Populate Cameroon geographic hierarchy (regions → divisions → councils).

Loads ``backend/data/cameroon_geography.json`` and upserts units into
``geographic_units`` using the same shape as the foundation seed:

  COUNTRY → REGION → DIVISION → COUNCIL

Idempotent:
  - Matches existing rows by ``unit_code`` (preferred) or by alias codes
  - Updates name/type/parent when a match is found
  - Creates missing units without deleting demo extras (e.g. TOWN Kumba)

Usage (from backend/):

  python scripts/populate_cameroon_geography.py
  python scripts/populate_cameroon_geography.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.models.geography import GeographicUnit

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "cameroon_geography.json"


def _load_tree() -> dict[str, Any]:
    if not DATA_PATH.is_file():
        raise SystemExit(f"Geography data file missing: {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _find_unit(db, unit_code: str, aliases: Optional[list[str]] = None) -> Optional[GeographicUnit]:
    for code in [unit_code, *(aliases or [])]:
        unit = db.query(GeographicUnit).filter(GeographicUnit.unit_code == code).first()
        if unit:
            return unit
    return None


def _upsert_node(
    db,
    node: dict[str, Any],
    *,
    parent_id: Optional[str],
    dry_run: bool,
    stats: dict[str, int],
) -> Optional[str]:
    """Upsert one node; returns geographic_unit_id (or None on dry-run create)."""
    unit_code = node["unit_code"]
    aliases = node.get("aliases") or []
    existing = _find_unit(db, unit_code, aliases)

    if existing:
        changed = False
        if existing.unit_name != node["unit_name"]:
            existing.unit_name = node["unit_name"]
            changed = True
        if existing.unit_type != node["unit_type"]:
            existing.unit_type = node["unit_type"]
            changed = True
        if existing.country_code != node.get("country_code"):
            existing.country_code = node.get("country_code")
            changed = True
        # Keep legacy demo codes (e.g. KUMBA-01) but attach under the canonical parent
        # when the unit was previously nested under a TOWN placeholder.
        if parent_id and existing.parent_id != parent_id:
            existing.parent_id = parent_id
            changed = True
        if existing.status != "ACTIVE":
            existing.status = "ACTIVE"
            changed = True
        if changed:
            stats["updated"] += 1
            action = "UPDATE"
        else:
            stats["unchanged"] += 1
            action = "KEEP"
        print(f"  {action:8} {existing.unit_type:10} {existing.unit_code:40} {existing.unit_name}")
        unit_id = existing.geographic_unit_id
    else:
        stats["created"] += 1
        print(f"  {'CREATE':8} {node['unit_type']:10} {unit_code:40} {node['unit_name']}")
        if dry_run:
            unit_id = None
        else:
            unit = GeographicUnit(
                parent_id=parent_id,
                unit_code=unit_code,
                unit_name=node["unit_name"],
                unit_type=node["unit_type"],
                country_code=node.get("country_code"),
            )
            db.add(unit)
            db.flush()
            unit_id = unit.geographic_unit_id

    for child in node.get("children") or []:
        _upsert_node(db, child, parent_id=unit_id, dry_run=dry_run, stats=stats)
    return unit_id


def _collect_codes(node: dict[str, Any], out: set[str]) -> None:
    out.add(node["unit_code"])
    for alias in node.get("aliases") or []:
        out.add(alias)
    for child in node.get("children") or []:
        _collect_codes(child, out)


def prune_orphans(db, root: dict[str, Any], *, dry_run: bool, stats: dict[str, int]) -> None:
    """Remove CM units absent from the data file when they have no tenant links/children."""
    from app.models.geography import TenantGeographicUnit

    known: set[str] = set()
    _collect_codes(root, known)
    # Preserve the demo Kumba TOWN row from foundation seed if present
    known.add("CM-SW-MEME-KUMBA")

    rows = (
        db.query(GeographicUnit)
        .filter(GeographicUnit.country_code == "CM")
        .order_by(GeographicUnit.unit_code)
        .all()
    )
    for unit in rows:
        if unit.unit_code in known:
            continue
        linked = (
            db.query(TenantGeographicUnit)
            .filter(TenantGeographicUnit.geographic_unit_id == unit.geographic_unit_id)
            .count()
        )
        kids = (
            db.query(GeographicUnit)
            .filter(GeographicUnit.parent_id == unit.geographic_unit_id)
            .count()
        )
        if linked or kids:
            print(
                f"  {'SKIP':8} orphan {unit.unit_type:10} {unit.unit_code:40} "
                f"(linked={linked}, children={kids})"
            )
            continue
        stats["pruned"] += 1
        print(f"  {'PRUNE':8} {unit.unit_type:10} {unit.unit_code:40} {unit.unit_name}")
        if not dry_run:
            db.delete(unit)


def populate(db, *, dry_run: bool = False, prune: bool = False) -> dict[str, int]:
    tree = _load_tree()
    meta = tree.get("_meta") or {}
    counts = meta.get("counts") or {}
    print(
        "Cameroon geography:",
        f"{counts.get('regions', '?')} regions,",
        f"{counts.get('divisions', '?')} divisions,",
        f"{counts.get('councils', '?')} councils",
    )
    if meta.get("hierarchy"):
        print("Hierarchy:", meta["hierarchy"])
    if dry_run:
        print("DRY RUN — no database writes")

    stats = {"created": 0, "updated": 0, "unchanged": 0, "pruned": 0}
    # Strip meta before walking children of the root country node
    root = {k: v for k, v in tree.items() if not k.startswith("_")}
    _upsert_node(db, root, parent_id=None, dry_run=dry_run, stats=stats)
    if prune:
        prune_orphans(db, root, dry_run=dry_run, stats=stats)
    if not dry_run:
        db.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print create/update actions without writing to the database",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete unlinked CM geography rows that are not in the data file",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        stats = populate(db, dry_run=args.dry_run, prune=args.prune)
        print(
            "Done:",
            f"created={stats['created']}",
            f"updated={stats['updated']}",
            f"unchanged={stats['unchanged']}",
            f"pruned={stats['pruned']}",
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
