# tests/unit/test_decorators.py
from flask import session
from app.utils import decorators
import pytest

def _make_dummy_view():
    @decorators.login_required
    def view():
        return "OK"
    return view

def test_login_required_redirects(flask_app):
    # ensure dummy auth.login endpoint exists in flask_app fixture (see earlier)
    view = _make_dummy_view()
    with flask_app.test_request_context('/x'):
        session.pop('user_id', None)
        resp = view()
        assert hasattr(resp, "status_code")
        assert resp.status_code in (301, 302)
        assert "/auth/login" in resp.headers.get("Location", "")

def test_login_required_allows(flask_app):
    view = _make_dummy_view()
    with flask_app.test_request_context('/x'):
        session['user_id'] = 99
        assert view() == "OK"
