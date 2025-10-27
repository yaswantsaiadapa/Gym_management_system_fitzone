# tests/unit/test_decorators.py
from flask import session
from app.utils import decorators
import pytest

def _make_dummy_view():
    @decorators.login_required
    def view_fn():
        # sentinel return value to prove it ran
        return "OK"
    return view_fn

def test_login_required_redirects_when_not_logged_in(flask_app):
    view = _make_dummy_view()
    with flask_app.test_request_context('/protected'):
        # ensure no user_id
        session.pop('user_id', None)
        response = view()
        # decorator should return a redirect (Flask Response)
        assert hasattr(response, "status_code")
        assert response.status_code in (301, 302)
        # Location should point to the dummy auth.login endpoint
        location = response.headers.get("Location", "")
        assert "/auth/login" in location

def test_login_required_allows_when_logged_in(flask_app):
    view = _make_dummy_view()
    with flask_app.test_request_context('/protected'):
        session['user_id'] = 42
        result = view()
        assert result == "OK"

def test_ajax_login_required_returns_401(flask_app):
    # Create a dummy function wrapped with ajax_login_required
    @decorators.ajax_login_required
    def sample_ajax():
        return {"ok": True}

    with flask_app.test_request_context('/ajax'):
        session.pop('user_id', None)
        resp, status = sample_ajax()
        assert status == 401
        assert isinstance(resp, dict)
        assert resp.get("error") == "Authentication required"
