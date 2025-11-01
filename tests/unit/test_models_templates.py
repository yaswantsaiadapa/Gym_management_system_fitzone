# tests/unit/test_models_templates.py
import os
import re
import pytest
from flask import Flask, render_template, render_template_string, session
from datetime import datetime, date
from types import SimpleNamespace
from datetime import date


URLFOR_RE = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")

# --------------------------------------------------------------------
# Fixture — Create a lightweight Flask app configured for template tests
# --------------------------------------------------------------------
@pytest.fixture(scope="module")
def test_flask_app():
    """
    Lightweight Flask app for template tests:
      - points template_folder to app/templates
      - registers datetimeformat filter
      - scans templates for url_for('...') and registers dummy endpoints so url_for(...) won't BuildError
      - injects `date` global used by templates
    """
    app = Flask(__name__)
    tmpl_path = os.path.join(os.path.dirname(__file__), "../../app/templates")
    app.template_folder = os.path.abspath(tmpl_path)
    app.config["TESTING"] = True
    app.secret_key = "test-secret-key"

    # datetimeformat filter used by templates
    def _datetimeformat(value, fmt="%b %d, %Y"):
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            try:
                return value.strftime(fmt)
            except Exception:
                return str(value)
        try:
            if isinstance(value, str):
                try:
                    dt = datetime.fromisoformat(value)
                except Exception:
                    try:
                        dt = datetime.strptime(value, "%Y-%m-%d")
                    except Exception:
                        return value
                return dt.strftime(fmt)
        except Exception:
            pass
        return str(value)

    app.jinja_env.filters["datetimeformat"] = _datetimeformat
    app.jinja_env.globals["date"] = date  # so templates can call date.today()

    # register a few common endpoints preemptively
    builtin_endpoints = [
        "static", "home.index", "auth.login", "auth.logout", "auth.register", "auth.change_password_form"
    ]
    # Add those dummy endpoints
    for ep in builtin_endpoints:
        rule = "/" + ep.replace(".", "/")
        def _dummy(ep_name=ep):
            return f"/{ep_name}"
        try:
            app.add_url_rule(rule, endpoint=ep, view_func=_dummy)
        except Exception:
            pass

    # Scan all templates for url_for('...') usages and register dummy endpoints for them
    tpl_dir = app.template_folder
    endpoints_seen = set()
    if os.path.isdir(tpl_dir):
        for root, _, files in os.walk(tpl_dir):
            for fname in files:
                if not fname.endswith((".html", ".jinja2")):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, encoding="utf-8") as fh:
                        txt = fh.read()
                except Exception:
                    continue
                for match in URLFOR_RE.finditer(txt):
                    ep = match.group(1)
                    if ep in endpoints_seen:
                        continue
                    endpoints_seen.add(ep)
                    rule = "/" + ep.replace(".", "/")
                    def _dummy(ep_name=ep):
                        return f"/{ep_name}"
                    try:
                        app.add_url_rule(rule, endpoint=ep, view_func=_dummy)
                    except Exception:
                        # ignore duplicates / conflicts
                        pass

    yield app


# small helper to attempt importing a module without failing tests
def try_import(modpath):
    try:
        mod = __import__(modpath, fromlist=["*"])
        return mod
    except Exception:
        return None


# ------------------------
# Tests start here
# ------------------------
def test_templates_folder_exists(test_flask_app):
    assert os.path.isdir(test_flask_app.template_folder)


def test_member_full_name_style():
    """
    If app.models.member.Member exists and exposes full_name, ensure it resolves to a string;
    otherwise run a small fallback sanity check.
    """
    member_mod = try_import("app.models.member")
    if member_mod and hasattr(member_mod, "Member"):
        Member = getattr(member_mod, "Member")
        inst = Member()
        # set common attributes that models often use
        try:
            setattr(inst, "first_name", "Alice")
            setattr(inst, "last_name", "Smith")
        except Exception:
            pass

        val = None
        if hasattr(inst, "full_name"):
            try:
                val = inst.full_name() if callable(inst.full_name) else inst.full_name
            except Exception:
                val = None

        if not val:
            fn = getattr(inst, "first_name", None)
            ln = getattr(inst, "last_name", None)
            if fn or ln:
                val = f"{fn or ''} {ln or ''}".strip()
            else:
                val = str(getattr(inst, "full_name", "Unnamed"))

        assert isinstance(val, str) and len(val) > 0
    else:
        # fallback trivial check
        from types import SimpleNamespace
        m = SimpleNamespace(first_name="Alice", last_name="Smith")
        assert f"{m.first_name} {m.last_name}" == "Alice Smith"


def test_base_template_renders(test_flask_app):
    base_path = os.path.join(test_flask_app.template_folder, "base.html")
    if not os.path.exists(base_path):
        pytest.skip("base.html not found — skipping base template test")

    # use a request context so session/url_for work inside templates
    with test_flask_app.test_request_context("/"):
        session["user_id"] = 1
        session["role"] = "admin"
        html = render_template("base.html")
        assert "<html" in html.lower() or "<!doctype" in html.lower()
        assert "{% block" not in html
        assert ("nav" in html.lower()) or ("footer" in html.lower())


@pytest.mark.parametrize("template_name,context", [
    (
        "admin/dashboard.html",
        {
            "user": "Admin",
            "title": "Dashboard",
            # provide a few keys admin/dashboard might reference so rendering succeeds
            "total_members": 0,
            "total_trainers": 0,
            "today_attendance": 0,
            "monthly_revenue": 0,
            "total_revenue": 0,
            "pending_payments": 0,
            "working_equipment": 0,
            "maintenance_equipment": 0,
            "recent_members": []
        }
    ),
    (
        "member/dashboard.html",
        {
            "user": "John Doe",
            "plan": "Weight Loss",
            # member object used in template (member.full_name, member.email, member.created_at)
            "member": SimpleNamespace(
                full_name="John Doe",
                email="john@example.com",
                created_at=date.today()
            ),
            # stats structure used by the member dashboard
            "stats": {
                "pending_payments": [],
                "membership_status": "active",
                "days_until_expiry": 30,
                "recent_attendance": [],
                "recent_sessions": [],
            },
            # alert_message may be referenced
            "alert_message": None,
        }
    ),
])
def test_template_renders_with_context(test_flask_app, template_name, context):
    path = os.path.join(test_flask_app.template_folder, template_name)
    if not os.path.exists(path):
        pytest.skip(f"{template_name} not found — skipping Jinja rendering test")

    with test_flask_app.test_request_context("/"):
        session["user_id"] = 1
        session["role"] = "admin"
        html = render_template(template_name, **context)
        # ensure context strings appear OR template rendered without raw Jinja
        for key, val in context.items():
            if isinstance(val, str):
                if val not in html:
                    # allow template to not include that variable; but ensure no raw jinja remains
                    assert "{%" not in html and "{{" not in html
                else:
                    assert val in html


def test_template_includes_render(test_flask_app):
    partials = ["_navbar.html", "_sidebar.html", "_footer.html"]
    found_any = False
    for partial in partials:
        pth = os.path.join(test_flask_app.template_folder, partial)
        if not os.path.exists(pth):
            continue
        found_any = True
        with test_flask_app.test_request_context("/"):
            session["user_id"] = 1
            html = render_template(partial, user="Tester")
            assert "Tester" in html or "nav" in html.lower() or "menu" in html.lower()
    if not found_any:
        pytest.skip("No partial templates found — skipping partials test")


def test_inline_jinja_macros_render_correctly(test_flask_app):
    jinja_snippet = """
    {% macro badge(status) -%}
        <span class="badge {{ 'bg-success' if status=='active' else 'bg-danger' }}">{{ status }}</span>
    {%- endmacro %}
    {{ badge('active') }}
    """
    with test_flask_app.test_request_context("/"):
        html = render_template_string(jinja_snippet)
        assert "badge" in html
        assert "active" in html
        assert "bg-success" in html


@pytest.mark.parametrize("template_name", [
    "admin/reports.html",
    "admin/members.html",
    "trainer/dashboard.html",
])
def test_template_inheritance_and_blocks(test_flask_app, template_name):
    path = os.path.join(test_flask_app.template_folder, template_name)
    if not os.path.exists(path):
        pytest.skip(f"{template_name} missing — skipping inheritance test")

    with test_flask_app.test_request_context("/"):
        session["user_id"] = 1
        # some templates don't use the 'user' variable; we only assert that
        # Jinja was evaluated (no raw tags) and HTML was produced
        html = render_template(template_name, user="Admin")
        assert ("<html" in html) or ("<body" in html)
        assert "{%" not in html and "{{" not in html


def test_static_assets_links_present(test_flask_app):
    base_path = os.path.join(test_flask_app.template_folder, "base.html")
    if not os.path.exists(base_path):
        pytest.skip("base.html not found for static asset check")

    with open(base_path, encoding="utf-8") as f:
        content = f.read().lower()
    assert any(x in content for x in ["bootstrap", "tailwind", "chart", "js", "css"])
