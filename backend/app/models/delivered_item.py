from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeliveredItem(Base):
    __tablename__ = "delivered_items"
    __table_args__ = (UniqueConstraint("source_id", "media_id", name="uq_delivered_source_media"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    media_id: Mapped[str] = mapped_column(String(128), nullable=False)
    first_run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
