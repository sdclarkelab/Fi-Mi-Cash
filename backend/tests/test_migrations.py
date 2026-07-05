import pytest
from sqlalchemy import create_engine, inspect, text

from app.db.migrations import run_startup_migrations


def _legacy_engine(tmp_path):
    """A transactions table as it exists in the live pre-migration DB."""
    engine = create_engine(f"sqlite:///{tmp_path}/legacy.db")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE transactions ("
            "id VARCHAR(36) PRIMARY KEY, date DATETIME, amount NUMERIC(10,2) NOT NULL, "
            "merchant VARCHAR, primary_category VARCHAR, subcategory VARCHAR, "
            "confidence FLOAT, description VARCHAR, excluded BOOLEAN NOT NULL, "
            "original_currency VARCHAR(3), original_amount NUMERIC(10,2), "
            "exchange_rate NUMERIC(10,6), exchange_rate_date DATE, "
            "card_type VARCHAR(50), source VARCHAR(20) NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO transactions (id, date, amount, merchant, primary_category, "
            "subcategory, confidence, description, excluded, source) "
            "VALUES ('t1', '2026-06-15 12:30:00', 1500, 'COFFEE SPOT', 'Food & Dining', "
            "'Coffee Shops', 0.9, 'test', 0, 'email')"
        ))
    return engine


def test_migration_adds_column_and_index(tmp_path):
    engine = _legacy_engine(tmp_path)
    run_startup_migrations(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("transactions")}
    assert "email_message_id" in columns
    with engine.connect() as conn:
        # SQLAlchemy's SQLite inspector does not reliably reflect partial
        # indexes — check sqlite_master directly.
        index = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='ix_transactions_email_message_id'"
        )).scalar()
        value = conn.execute(
            text("SELECT email_message_id FROM transactions WHERE id='t1'")
        ).scalar()
    assert index == "ix_transactions_email_message_id"
    assert value is None  # existing rows stay, with NULL message id

    # The migrated index enforces uniqueness of non-NULL message ids
    with pytest.raises(Exception):
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE transactions SET email_message_id='dup' WHERE id='t1'"
            ))
            conn.execute(text(
                "INSERT INTO transactions (id, date, amount, excluded, source, email_message_id) "
                "VALUES ('t2', '2026-06-16 10:00:00', 900, 0, 'email', 'dup')"
            ))


def test_migration_is_idempotent(tmp_path):
    engine = _legacy_engine(tmp_path)
    run_startup_migrations(engine)
    run_startup_migrations(engine)  # second run must not raise

    columns = [c["name"] for c in inspect(engine).get_columns("transactions")]
    assert columns.count("email_message_id") == 1


def test_migration_noop_without_transactions_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/empty.db")
    run_startup_migrations(engine)  # fresh DB before create_all: must not raise
