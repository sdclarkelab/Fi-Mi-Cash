from sqlalchemy import Column, String, DateTime

from app.db.base_class import Base  # Import existing Base instead of creating a new one


class SyncInfoModel(Base):
    __tablename__ = "sync_info"

    id = Column(String, primary_key=True, default="last_sync")
    last_sync_date = Column(DateTime, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
