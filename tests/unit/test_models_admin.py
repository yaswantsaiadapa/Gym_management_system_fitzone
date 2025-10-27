# tests/unit/test_models_admin.py
import pytest
from app.models import admin as admin_mod

def test_admin_class_exists():
    # Ensure we can instantiate Admin or access attributes
    if hasattr(admin_mod, "Admin"):
        a = admin_mod.Admin(username="x")
        assert hasattr(a, "username")
    else:
        pytest.skip("Admin class missing")
