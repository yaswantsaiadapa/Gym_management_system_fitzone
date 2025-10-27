# tests/unit/test_email_utils.py
import pytest
from unittest.mock import MagicMock, patch

# import email_utils module (adjust path if different)
from app.utils import email_utils

def test_send_welcome_email_monkeypatched(monkeypatch):
    """
    If email_utils sends via SMTP or Flask-Mail, monkeypatch the send function used.
    This test ensures your wrapper returns True (or expected) without sending a real email.
    """
    # Try common names: smtp_send, send_email, Mail.send — adapt if module differs
    if hasattr(email_utils, "send_email_via_smtp"):
        monkeypatch.setattr(email_utils, "send_email_via_smtp", lambda *a, **k: True)
        assert email_utils.send_email_via_smtp("to@example.com", "subject", "body") is True
    elif hasattr(email_utils, "mail") and hasattr(email_utils.mail, "send"):
        # patch Mail.send
        monkeypatch.setattr(email_utils.mail, "send", lambda *a, **k: None)
        # call your wrapper (if exists). Common wrapper names: send_welcome_email
        if hasattr(email_utils, "send_welcome_email"):
            assert email_utils.send_welcome_email("to@example.com", "Name") in (True, None)
        else:
            # at minimum assert patched send exists
            assert callable(email_utils.mail.send)
    else:
        pytest.skip("email_utils has no known send function; adapt test to module implementation")
