# tests/unit/test_models_equipment.py
import pytest
from datetime import date
from app.models import equipment as equipment_module

# A small helper to produce a "full" DB row tuple matching the
# CREATE TABLE ordering used in the Equipment._from_row mapping.

def make_row(
    id=1,
    name="Treadmill Pro X1",
    category="Cardio",
    brand="TechFit",
    model="TX-2024",
    purchase_date="2024-01-01",
    warranty_end_date="2026-01-01",
    status="working",
    last_maintenance_date=None,
    next_maintenance_date=None,
    maintenance_notes=None,
    location="Cardio Area",
    created_at="2024-01-01 00:00:00",
):
    return (
        id,
        name,
        category,
        brand,
        model,
        purchase_date,
        warranty_end_date,
        status,
        last_maintenance_date,
        next_maintenance_date,
        maintenance_notes,
        location,
        created_at,
    )


def test_get_all_and_get_by_id_and_get_working_counts(monkeypatch, flask_app):
    """Test fetching helpers: get_all, get_by_id, get_working, and count helpers."""
    # Prepare fake rows and counts
    row1 = make_row(id=1, name="Treadmill")
    row2 = make_row(id=2, name="Bike", status="maintenance")
    all_rows = [row1, row2]
    working_rows = [row1]
    counts = {"working": [(1,)], "maintenance": [(1,)], "out": [(0,)]}

    def fake_execute_query(query, params=(), db_path=None, fetch=False):
        q = (query or "").lower()
        if "select * from equipment order by name" in q:
            return all_rows if fetch else None
        if "where id = ?" in q:
            # return first row if param == 1 else second
            return [row1] if params and params[0] == 1 else [row2]
        if 'where status = "working"' in q and "order by name" in q:
            return working_rows
        if "count(*) from equipment where status = \"working\"" in q:
            return counts["working"]
        if "count(*) from equipment where status = \"maintenance\"" in q:
            return counts["maintenance"]
        if "count(*) from equipment where status = \"out_of_order\"" in q:
            return counts["out"]
        # default
        return []

    monkeypatch.setattr(equipment_module, "execute_query", fake_execute_query)

    with flask_app.app_context():
        all_eq = equipment_module.Equipment.get_all()
        assert isinstance(all_eq, list)
        assert any(isinstance(e, equipment_module.Equipment) for e in all_eq)
        assert any(e.name == "Treadmill" for e in all_eq)

        eq = equipment_module.Equipment.get_by_id(1)
        assert isinstance(eq, equipment_module.Equipment)
        assert eq.id == 1 and eq.name == "Treadmill"

        working = equipment_module.Equipment.get_working()
        assert isinstance(working, list)
        assert working[0].status == "working"

        assert equipment_module.Equipment.get_working_count() == 1
        assert equipment_module.Equipment.get_maintenance_count() == 1
        assert equipment_module.Equipment.get_out_of_order_count() == 0


def test_save_insert_and_update(monkeypatch, flask_app):
    """
    Test save() for insert (no id) and update (with id).
    The fake execute_query will return a lastrowid for insert.
    """
    calls = {"queries": []}

    def fake_execute_query(query, params=(), db_path=None, fetch=False):
        calls["queries"].append((query.strip().split()[0].upper(), params))
        qlow = (query or "").lower()
        if qlow.strip().startswith("insert into equipment"):
            # simulate returning lastrowid (int)
            return 42
        if qlow.strip().startswith("update equipment"):
            # simulate update: return None (real function returns lastrowid only for inserts)
            return None
        return None

    monkeypatch.setattr(equipment_module, "execute_query", fake_execute_query)

    # INSERT path
    eq = equipment_module.Equipment(name="New Machine", category="Strength")
    with flask_app.app_context():
        new_id = eq.save()
    assert new_id == 42
    assert eq.id == 42
    assert any(q[0] == "INSERT" for q in calls["queries"])

    # UPDATE path
    calls["queries"].clear()
    eq.name = "Updated Machine"
    with flask_app.app_context():
        ret = eq.save()
    # update returns self.id
    assert ret == 42
    assert any(q[0] == "UPDATE" for q in calls["queries"])


def test_delete_and_status_helpers(monkeypatch, flask_app):
    """Test delete(), mark_for_maintenance(), mark_as_working(), mark_out_of_order(), and boolean helpers."""
    executed = []

    def fake_execute_query(query, params=(), db_path=None, fetch=False):
        executed.append((query, params, fetch))
        ql = (query or "").lower()
        if ql.strip().startswith("delete from equipment"):
            return None
        if ql.strip().startswith("insert into equipment"):
            return 7  # new id
        if ql.strip().startswith("update equipment"):
            return None
        return None

    monkeypatch.setattr(equipment_module, "execute_query", fake_execute_query)

    # delete without id should return False
    eq = equipment_module.Equipment(name="Tmp")
    with flask_app.app_context():
        assert eq.delete() is False

    # mark_for_maintenance should set fields and call save (insert)
    eq2 = equipment_module.Equipment(name="Machine A")
    with flask_app.app_context():
        new_id = eq2.mark_for_maintenance(notes="Needs belt", next_date="2025-06-01")
    assert isinstance(new_id, int) and new_id == 7
    assert eq2.status == "maintenance"
    assert eq2.maintenance_notes == "Needs belt"
    assert eq2.last_maintenance_date is not None

    # mark_as_working (update)
    # ensure id present so save goes through update branch
    eq2.id = 7
    with flask_app.app_context():
        nid = eq2.mark_as_working()
    assert nid == 7
    assert eq2.is_working()

    # mark_out_of_order
    with flask_app.app_context():
        res = eq2.mark_out_of_order(notes="Broken motor")
    assert res == 7
    assert eq2.is_out_of_order()
    assert eq2.maintenance_notes == "Broken motor"

    # delete (with id) -> should call delete query and return True
    with flask_app.app_context():
        ok = eq2.delete()
    assert ok is True
    assert any("delete from equipment" in q[0].lower() for q in executed)


def test_from_row_handles_short_rows(monkeypatch, flask_app):
    """
    Ensure _from_row gracefully handles rows that are shorter than full column count
    (common when SELECT projects fewer columns).
    """
    # Provide a short row (id, name, category only)
    short_row = (5, "ShortRowMachine", "Misc")
    # No DB call needed; call _from_row directly
    inst = equipment_module.Equipment._from_row(short_row)
    assert isinstance(inst, equipment_module.Equipment)
    assert inst.id == 5
    assert inst.name == "ShortRowMachine"
    # missing fields should be None or default
    assert inst.brand is None
    assert inst.status == "working" or inst.status is not None
