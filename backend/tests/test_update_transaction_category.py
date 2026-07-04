import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.api_v1.dependencies import get_transaction_service
from app.db.base_class import Base
from app.main import app
from app.models.transaction_model import TransactionModel
from app.services.transaction_service import TransactionService

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


@pytest.fixture()
def client(db_session):
    # Gmail/classifier are never touched by the category-update path.
    service = TransactionService(gmail_service=None, classifier=None, db=db_session)
    app.dependency_overrides[get_transaction_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.pop(get_transaction_service, None)


@pytest.fixture()
def seeded_transaction(db_session):
    tx = TransactionModel(
        id=str(uuid.uuid4()),
        date=datetime(2026, 6, 15, 12, 30),
        amount=1500,
        merchant="COFFEE SPOT",
        primary_category="Food & Dining",
        subcategory="Coffee Shops",
        confidence=0.9,
        description="test",
        excluded=False,
        source="email",
    )
    db_session.add(tx)
    db_session.commit()
    return tx


def test_update_category_persists_and_returns_transaction(client, db_session, seeded_transaction):
    response = client.patch(
        f"/api/v1/transactions/{seeded_transaction.id}/category",
        json={"primary_category": "Entertainment", "subcategory": "Streaming"},
        headers=AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == seeded_transaction.id
    assert body["primary_category"] == "Entertainment"
    assert body["subcategory"] == "Streaming"

    db_session.refresh(seeded_transaction)
    assert seeded_transaction.primary_category == "Entertainment"
    assert seeded_transaction.subcategory == "Streaming"


def test_update_category_leaves_other_fields_untouched(client, db_session, seeded_transaction):
    response = client.patch(
        f"/api/v1/transactions/{seeded_transaction.id}/category",
        json={"primary_category": "Entertainment", "subcategory": "Streaming"},
        headers=AUTH,
    )
    assert response.status_code == 200

    db_session.refresh(seeded_transaction)
    assert seeded_transaction.merchant == "COFFEE SPOT"
    assert float(seeded_transaction.amount) == 1500
    assert seeded_transaction.excluded is False


def test_update_category_unknown_id_returns_404(client):
    response = client.patch(
        f"/api/v1/transactions/{uuid.uuid4()}/category",
        json={"primary_category": "Entertainment", "subcategory": ""},
        headers=AUTH,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


def test_update_category_requires_primary_category(client, seeded_transaction):
    response = client.patch(
        f"/api/v1/transactions/{seeded_transaction.id}/category",
        json={"subcategory": "Streaming"},
        headers=AUTH,
    )
    assert response.status_code == 422
