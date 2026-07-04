from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.api_v1.dependencies import get_transaction_service
from app.core.exceptions import GmailAPIError
from app.db.base_class import Base
from app.db.crud import SyncInfoCrud
from app.main import app
from app.services.transaction_service import TransactionService
from sync_fakes import FakeClassifier, make_email

AUTH = {"X-API-Key": "test-api-key"}

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class OneBatchGmail:
    def __init__(self, emails):
        self.emails = emails

    def get_messages(self, query):
        return self.emails


class FailingGmail:
    def get_messages(self, query):
        raise GmailAPIError("Gmail unavailable")


@pytest.fixture()
def make_client(db_session):
    """Factory: build a TestClient whose service uses the given Gmail fake.

    Teardown always removes the override (the deferred fixture-cleanup
    pattern from the security-lockdown review).
    """
    def _make(gmail):
        service = TransactionService(
            gmail_service=gmail, classifier=FakeClassifier(), db=db_session
        )
        app.dependency_overrides[get_transaction_service] = lambda: service
        return TestClient(app)

    yield _make
    app.dependency_overrides.pop(get_transaction_service, None)


def test_sync_status_empty(make_client):
    response = make_client(OneBatchGmail([])).get("/api/v1/sync/status", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {
        "last_sync_date": None,
        "synced_start_date": None,
        "synced_end_date": None,
    }


def test_sync_status_reports_range(make_client, db_session):
    SyncInfoCrud.update_last_sync(db_session, datetime(2026, 6, 1), datetime(2026, 6, 30))
    body = make_client(OneBatchGmail([])).get("/api/v1/sync/status", headers=AUTH).json()
    assert body["synced_start_date"] == "2026-06-01T00:00:00"
    assert body["synced_end_date"] == "2026-06-30T00:00:00"
    assert body["last_sync_date"] is not None


def test_post_sync_returns_counts(make_client):
    client = make_client(OneBatchGmail([make_email("m1")]))
    response = client.post(
        "/api/v1/sync",
        json={"start_date": "2026-06-14T00:00:00", "end_date": "2026-06-16T23:59:59"},
        headers=AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] == 1
    assert body["stored"] == 1
    assert body["failed"] == 0
    assert body["last_sync_date"] is not None


def test_post_sync_rejects_inverted_range(make_client):
    response = make_client(OneBatchGmail([])).post(
        "/api/v1/sync",
        json={"start_date": "2026-06-16T00:00:00", "end_date": "2026-06-14T00:00:00"},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_post_sync_requires_body(make_client):
    response = make_client(OneBatchGmail([])).post("/api/v1/sync", json={}, headers=AUTH)
    assert response.status_code == 422


def test_post_sync_gmail_failure_returns_502(make_client):
    response = make_client(FailingGmail()).post(
        "/api/v1/sync",
        json={"start_date": "2026-06-14T00:00:00", "end_date": "2026-06-16T23:59:59"},
        headers=AUTH,
    )
    assert response.status_code == 502
    assert "Gmail" in response.json()["detail"]


def test_sync_requires_api_key(make_client):
    response = make_client(OneBatchGmail([])).get("/api/v1/sync/status")
    assert response.status_code == 401
