from sqlalchemy import inspect, text

from app.core.logger import logger


def run_startup_migrations(engine) -> None:
    """Idempotent, additive schema fixes that create_all() can't apply to
    already-existing tables (this project has no alembic)."""
    inspector = inspect(engine)
    if "transactions" not in inspector.get_table_names():
        return  # fresh DB: create_all() builds the full schema

    columns = {col["name"] for col in inspector.get_columns("transactions")}
    with engine.begin() as conn:
        if "email_message_id" not in columns:
            logger.info("Migrating: adding transactions.email_message_id")
            conn.execute(text(
                "ALTER TABLE transactions ADD COLUMN email_message_id VARCHAR"
            ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_email_message_id "
            "ON transactions(email_message_id) WHERE email_message_id IS NOT NULL"
        ))
