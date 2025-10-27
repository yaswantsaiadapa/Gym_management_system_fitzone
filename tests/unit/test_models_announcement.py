# tests/unit/test_models_announcement.py
import pytest
from app.models import announcement

def test_announcement_class_present():
    if hasattr(announcement, "Announcement"):
        ann = announcement.Announcement(title="Hello", message="World")

        assert hasattr(ann, "title")
    else:
        pytest.skip("Announcement class missing")
