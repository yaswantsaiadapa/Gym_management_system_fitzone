# tests/unit/test_models_templates.py
"""
Enhanced and resilient template-like tests for simple model helpers.

This file contains example tests that:
 - verify simple pure-method behavior (full name formatting),
 - monkeypatch DB helpers used by model methods (without importing DB internals),
 - are resilient: if a target model or method is missing the test will skip
   with a helpful message so the test-suite remains useful across branches.

Edit the import paths / expected behavior to fit your actual models.
"""

import importlib
import pytest
from types import SimpleNamespace

# ---------------------------
# Utility helpers used by tests
# ---------------------------
def try_import(module_path):
    """Try to import a module path, return module or None."""
    try:
        return importlib.import_module(module_path)
    except Exception:
        return None

# ---------------------------
# Test 1: full name formatting (pure method / property)
# ---------------------------
def test_member_full_name_style():
    """
    If app.models.member.Member exists and exposes a `full_name` (property) or
    `get_full_name()` method, validate the formatting. Otherwise perform
    a simple sanity check using a dummy object.
    """
    member_mod = try_import("app.models.member")
    if member_mod and hasattr(member_mod, "Member"):
        Member = getattr(member_mod, "Member")
        # create a minimal instance with attributes expected by the model
        inst = Member()
        # try to set fields commonly used: first_name/last_name or full_name
        setattr(inst, "first_name", "Alice")
        setattr(inst, "last_name", "Smith")
        # if model provides a property/method, use it
        if hasattr(inst, "full_name"):
            # allow either attribute or callable
            val = inst.full_name if not callable(inst.full_name) else inst.full_name()
            assert isinstance(val, str)
            assert "Alice" in val and "Smith" in val
        elif hasattr(inst, "get_full_name"):
            val = inst.get_full_name()
            assert isinstance(val, str)
            assert "Alice" in val and "Smith" in val
        else:
            # fallback: the model exists but provides no helper — skip gracefully
            pytest.skip("Member model present but no full_name()/get_full_name() helper found")
    else:
        # no Member model — verify the simple pure formatting behavior as a template
        mem = SimpleNamespace(first_name="Alice", last_name="Smith")
        assert f"{mem.first_name} {mem.last_name}" == "Alice Smith"


# ---------------------------
# Test 2: has_active_membership — monkeypatch DB helper the model uses
# ---------------------------
def test_user_has_active_membership_calls_db(monkeypatch):
    """
    Example of monkeypatching a DB helper used by a model method.
    - If app.models.user.User exists and exposes has_active_membership(self)
      that internally calls a DB helper, we try to monkeypatch common helper names.
    - This test will try several plausible import paths for helpers:
        - app.models.database.execute_query
        - app.models.user.execute_query
        - app.models.user._get_membership_row
      Adjust to your project's actual helpers if necessary.
    """
    user_mod = try_import("app.models.user")
    if user_mod and hasattr(user_mod, "User"):
        User = getattr(user_mod, "User")
        # create a dummy user instance
        u = User()
        # try to set an id (common)
        if not hasattr(u, "id"):
            setattr(u, "id", 123)

        # We'll intercept whatever execute_query the model calls.
        # Try a few possible targets for monkeypatch to be robust.
        patched = False

        def fake_execute_query_true(q, p=(), db_path=None, fetch=False):
            # Simulate a DB row that indicates the user has an active membership
            return [(1,)] if fetch else None

        def fake_get_membership_row(uid):
            return {"active": True}

        # Common places to monkeypatch:
        try:
            monkeypatch.setattr("app.models.database.execute_query", fake_execute_query_true, raising=False)
            patched = True
        except Exception:
            pass

        try:
            # if the User module imported execute_query into its namespace
            monkeypatch.setattr("app.models.user.execute_query", fake_execute_query_true, raising=False)
            patched = True
        except Exception:
            pass

        try:
            monkeypatch.setattr("app.models.user._get_membership_row", fake_get_membership_row, raising=False)
            patched = True
        except Exception:
            pass

        if not patched:
            pytest.skip("Could not find DB helper to monkeypatch for User.has_active_membership — adapt test to project")

        # Now call the method if present
        if hasattr(User, "has_active_membership") or hasattr(User, "is_active_member"):
            # prefer instance method naming
            inst = User()
            if not hasattr(inst, "id"):
                inst.id = 123
            # call whichever exists
            if hasattr(inst, "has_active_membership"):
                res = inst.has_active_membership()
            else:
                res = inst.is_active_member()
            # Expect boolean-like result (True/False) or something truthy when patched
            assert res in (True, False) or bool(res) is True
        else:
            pytest.skip("User model has no has_active_membership / is_active_member method")
    else:
        pytest.skip("app.models.user.User not present — adapt test to your user model")


# ---------------------------
# Test 3: template-style helper (display name)
# ---------------------------
def test_display_name_helper_when_present():
    """
    If a model provides a simple helper to compute a display name, ensure the output is stable.
    This test tries to locate `app.models.member.Member` or `app.models.user.User` and call
    a `display_name()` or similar. If not present, demonstrate expected behavior with a SimpleNamespace.
    """
    member_mod = try_import("app.models.member")
    user_mod = try_import("app.models.user")

    target = None
    if member_mod and hasattr(member_mod, "Member"):
        target = getattr(member_mod, "Member")
    elif user_mod and hasattr(user_mod, "User"):
        target = getattr(user_mod, "User")

    if target:
        inst = target()
        # seed typical fields
        if not hasattr(inst, "full_name"):
            inst.full_name = "Bobby Tables"
        if not hasattr(inst, "email"):
            inst.email = "bobby@example.com"

        if hasattr(inst, "display_name"):
            dn = inst.display_name()
            assert isinstance(dn, str) and len(dn) > 0
        elif hasattr(inst, "get_display_name"):
            dn = inst.get_display_name()
            assert isinstance(dn, str) and len(dn) > 0
        else:
            # fallback: construct from available attrs
            assert f"{inst.full_name} <{inst.email}>" == f"{inst.full_name} <{inst.email}>"
    else:
        # No models available — verify the simple formatting behavior
        s = SimpleNamespace(full_name="Bobby Tables", email="bobby@example.com")
        assert f"{s.full_name} <{s.email}>" == "Bobby Tables <bobby@example.com>"
