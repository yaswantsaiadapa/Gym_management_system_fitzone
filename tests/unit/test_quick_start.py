# tests/unit/test_quick_start.py
from app.utils import helpers, decorators
from flask import session

def test_helpers_smoke():
    assert helpers.calculate_bmi(60, 165) is not None

def test_decorator_smoke(flask_app):
    @decorators.login_required
    def v(): return "OK"
    with flask_app.test_request_context('/'):
        session.pop('user_id', None)
        resp = v()
        assert resp.status_code in (301, 302)
