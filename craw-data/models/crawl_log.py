from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from models.base import Base
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CrawlLog(Base):
    """
    Nhật ký mỗi lần chạy spider.
    Hiển thị trên Admin Dashboard (UC06).
    """

    __tablename__ = "crawl_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    spider_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        comment="running | success | failed | partial",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    records_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # "scheduler" hoặc "admin:<user_uuid>"
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CrawlLog spider={self.spider_name!r} "
            f"status={self.status!r} "
            f"started={self.started_at}>"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Thời gian chạy tính bằng giây (None nếu chưa kết thúc)."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def total_records(self) -> int:
        return self.records_new + self.records_updated + self.records_failed
