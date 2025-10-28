import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app.routes.auth import auth_bp


@pytest.fixture
def app():
    """Create Flask app with auth blueprint."""
    app = Flask(__name__)
    app.secret_key = "testing_secret"
    app.register_blueprint(auth_bp)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# -------------------------
# Basic GET routes
# -------------------------
@patch("app.routes.auth.render_template", return_value="mocked_template")
def test_login_page_loads(mock_render, client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    mock_render.assert_called_once_with("auth/login_select.html")


@patch("app.routes.auth.render_template", return_value="mocked_template")
def test_login_form_valid_role(mock_render, client):
    resp = client.get("/auth/login/admin")
    assert resp.status_code == 200
    mock_render.assert_called_once_with("auth/login_form.html", role="admin")


# -------------------------
# Login POST
# -------------------------
@patch("app.routes.auth.redirect", return_value="redirected")
@patch("app.routes.auth.url_for", return_value="/admin/dashboard")
@patch("app.routes.auth.User.authenticate")
def test_login_post_success_admin(mock_auth, mock_url, mock_redirect, client):
    """Simulate successful admin login."""
    user_mock = MagicMock(
        id=1, username="admin", full_name="Admin", role="admin", email="a@a.com"
    )
    mock_auth.return_value = user_mock

    resp = client.post(
        "/auth/login/admin",
        data={"username": "admin", "password": "123"},
    )
    assert resp.status_code == 200
    mock_redirect.assert_called()


@patch("app.routes.auth.render_template", return_value="mocked_template")
@patch("app.routes.auth.User.authenticate", return_value=None)
def test_login_post_invalid(mock_auth, mock_render, client):
    """Invalid login → should redirect and flash."""
    resp = client.post(
        "/auth/login/member",
        data={"username": "x", "password": "y"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    mock_auth.assert_called_once()


# -------------------------
# Forgot Password
# -------------------------
@patch("app.routes.auth.send_password_reset_email")
@patch("app.routes.auth.redirect", return_value="redirected")
@patch("app.routes.auth.url_for", return_value="/reset")
def test_forgot_password_post_existing_user(mock_url, mock_redirect, mock_email, app, client):
    """Test forgot password when user exists."""
    with app.app_context():
        with patch("app.models.database.execute_query", return_value=[{"id": 1}]):
            resp = client.post("/auth/forgot_password", data={"email": "user@x.com"})
            assert resp.status_code == 200
            mock_email.assert_called_once()


@patch("app.routes.auth.redirect", return_value="redirected")
def test_forgot_password_post_no_email(mock_redirect, client):
    resp = client.post("/auth/forgot_password", data={})
    assert resp.status_code == 200
    mock_redirect.assert_called()


# -------------------------
# Change Password
# -------------------------
@patch("app.routes.auth.redirect", return_value="redirected")
@patch("app.routes.auth._get_bcrypt")
@patch("app.routes.auth.User.get_by_id")
def test_change_password_post_success(mock_get_by_id, mock_bcrypt, mock_redirect, client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"

    user_mock = MagicMock(password_hash="old")
    mock_get_by_id.return_value = user_mock
    bcrypt_mock = MagicMock(check_password_hash=lambda a, b: True)
    mock_bcrypt.return_value = bcrypt_mock
    user_mock.update_password = MagicMock(return_value=True)

    resp = client.post(
        "/auth/change_password",
        data={
            "current_password": "old",
            "new_password": "newpass",
            "confirm_password": "newpass",
        },
    )
    assert resp.status_code == 200
    mock_redirect.assert_called()


# -------------------------
# Reset Password
# -------------------------
@patch("app.routes.auth.redirect", return_value="redirected")
@patch("app.routes.auth.flash")
@patch("app.routes.auth.url_for", return_value="/auth/login")
@patch("app.routes.auth._get_bcrypt")
def test_reset_password_valid_token(mock_bcrypt, mock_url, mock_flash, mock_redirect, app, client):
    with app.app_context():
        bcrypt_mock = MagicMock()
        bcrypt_mock.generate_password_hash.return_value = b"hashed"
        mock_bcrypt.return_value = bcrypt_mock

        with patch("app.models.database.execute_query") as mock_exec:
            mock_exec.side_effect = [
                [{"id": 1}],  # token valid
                None,         # password update
            ]
            resp = client.post(
                "/auth/reset_password/securetoken",
                data={"new_password": "newpass", "confirm_password": "newpass"},
            )
            assert resp.status_code == 200
            mock_redirect.assert_called()


@patch("app.routes.auth.redirect", return_value="redirected")
@patch("app.routes.auth.flash")
def test_reset_password_invalid_token(mock_flash, mock_redirect, app, client):
    with app.app_context():
        with patch("app.models.database.execute_query", return_value=[]):
            resp = client.get("/auth/reset_password/badtoken")
            assert resp.status_code == 200
            mock_flash.assert_called_with("Invalid or expired password reset link!", "danger")
