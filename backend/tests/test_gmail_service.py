import base64
from unittest.mock import MagicMock

from app.services.gmail_service import GmailService


def _fake_gmail_api():
    service = MagicMock()
    service.users().messages().get().execute.return_value = {
        "internalDate": "1750000000000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Transaction Approved"},
                {"name": "From", "value": "no-reply-ncbcardalerts@jncb.com"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"hello").decode()},
        },
    }
    return service


def test_fetch_email_message_carries_gmail_message_id():
    gs = GmailService()
    gs._service = _fake_gmail_api()
    email = gs._fetch_email_message("abc123")
    assert email.message_id == "abc123"
    assert email.body == "hello"
