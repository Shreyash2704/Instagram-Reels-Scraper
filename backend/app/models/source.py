from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.run import Run


class SourceType(str, enum.Enum):
    hashtag = "hashtag"
    profile = "profile"
    post_url = "post_url"
    profile_tagged = "profile_tagged"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list[Run]] = relationship("Run", back_populates="source")
