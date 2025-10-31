import pytest
from datetime import date
from types import SimpleNamespace
from app.models import announcement as ann_module


@pytest.fixture(autouse=True)
def mock_flask_context(monkeypatch):
    """Provide mock current_app and database path for all tests."""
    class MockApp:
        config = {"DATABASE_PATH": "test_db.sqlite"}
    
    monkeypatch.setattr(ann_module, "current_app", MockApp())


@pytest.fixture
def mock_execute_query(monkeypatch):
    """Mock execute_query for database operations."""
    mock_db = {}

    def fake_execute_query(query, params=(), db_path=None, fetch=False):
        # Simulate DB fetches
        if "SELECT" in query:
            if "WHERE id =" in query:
                return [[1, "Title", "Body", "info", "all", 1, 1, "2025-01-01", "2025-12-31", 1, "2025-01-01 12:00:00"]]
            elif "created_by" in query:
                return [[2, "Trainer Note", "Keep going!", "info", "trainer", 1, 1, None, None, 5, "2025-02-01 12:00:00"]]
            else:
                return [
                    [1, "Title1", "Body1", "info", "all", 1, 1, None, None, 1, "2025-01-01 12:00:00"],
                    [2, "Title2", "Body2", "alert", "member", 0, 1, None, None, 2, "2025-01-02 12:00:00"]
                ]
        # Simulate insert returning new ID
        elif "INSERT" in query:
            new_id = len(mock_db) + 1
            mock_db[new_id] = params
            return new_id
        # Simulate update
        elif "UPDATE" in query:
            return True
        return None

    monkeypatch.setattr(ann_module, "execute_query", fake_execute_query)
    return fake_execute_query


# ------------------------------
# BASIC CLASS STRUCTURE TESTS
# ------------------------------

def test_announcement_class_exists():
    """Check if Announcement class exists and has core attributes."""
    assert hasattr(ann_module, "Announcement")
    ann = ann_module.Announcement(title="Hello", content="World")
    assert ann.title == "Hello"
    assert hasattr(ann, "save")
    assert hasattr(ann, "get_all")


# ------------------------------
# FETCHING TESTS
# ------------------------------

def test_get_all_returns_objects(mock_execute_query):
    anns = ann_module.Announcement.get_all()
    assert isinstance(anns, list)
    assert all(isinstance(a, ann_module.Announcement) for a in anns)
    assert anns[0].title.startswith("Title")


def test_get_by_id_returns_single(mock_execute_query):
    ann = ann_module.Announcement.get_by_id(1)
    assert isinstance(ann, ann_module.Announcement)
    assert ann.id == 1
    assert ann.title == "Title"


def test_get_by_creator_returns_list(mock_execute_query):
    anns = ann_module.Announcement.get_by_creator(5)
    assert isinstance(anns, list)
    assert anns[0].created_by == 5


def test_get_public_announcements(mock_execute_query):
    anns = ann_module.Announcement.get_public_announcements()
    assert isinstance(anns, list)
    assert all(isinstance(a, ann_module.Announcement) for a in anns)


def test_get_for_role_filters(mock_execute_query):
    anns = ann_module.Announcement.get_for_role("trainer")
    assert isinstance(anns, list)
    assert all(isinstance(a, ann_module.Announcement) for a in anns)


# ------------------------------
# SAVE / UPDATE / DEACTIVATE TESTS
# ------------------------------

def test_save_new_announcement_returns_id(mock_execute_query):
    ann = ann_module.Announcement(title="SaveTest", content="Something", is_public=True)
    result = ann.save()
    assert isinstance(result, int)
    assert ann.id == result


def test_save_existing_announcement_updates(mock_execute_query):
    ann = ann_module.Announcement(id=1, title="Old", content="Updated content")
    result = ann.save()
    assert result == 1  # mock returns True for updates


def test_deactivate_sets_flag(mock_execute_query):
    ann = ann_module.Announcement(id=1, title="DeactivateTest", is_active=True)
    ann.deactivate()
    assert ann.is_active is False


def test_deactivate_unsaved_raises():
    ann = ann_module.Announcement()
    with pytest.raises(ValueError):
        ann.deactivate()
