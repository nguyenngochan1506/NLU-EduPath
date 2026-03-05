from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from models.base import Base
from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy import BigInteger, Boolean, DateTime, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# ============================================================
# SQLAlchemy ORM Model
# ============================================================


class University(Base):
    __tablename__ = "universities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID khóa chính – sinh tự động phía Python",
    )
    university_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Mã trường do Bộ GD&ĐT cấp (VD: QSB, BKA)",
    )
    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Tên đầy đủ",
    )
    short_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Tên viết tắt (VD: HUST, UEH)",
    )
    university_type: Mapped[Optional[str]] = mapped_column(
        String(25),
        nullable=True,
        comment="public | private | foreign_affiliated",
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        comment="north | central | south",
    )
    province: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    admission_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tuition_min: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Học phí thấp nhất VNĐ/năm",
    )
    tuition_max: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Học phí cao nhất VNĐ/năm",
    )
    established_year: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Thời điểm thu thập dữ liệu",
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL trang đã crawl",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    admission_scores: Mapped[list["AdmissionScore"]] = relationship(  # noqa: F821
        "AdmissionScore", back_populates="university", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<University code={self.university_code!r} name={self.name!r}>"


# ============================================================
# Pydantic Schemas  (dùng để validate trong ValidationPipeline)
# ============================================================


class UniversityCreateSchema(BaseModel):
    """Schema validate dữ liệu thô từ spider trước khi lưu DB."""

    university_code: str
    name: str
    short_name: Optional[str] = None
    university_type: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    admission_url: Optional[str] = None
    logo_url: Optional[str] = None
    tuition_min: Optional[int] = None
    tuition_max: Optional[int] = None
    established_year: Optional[int] = None
    scraped_at: datetime
    source_url: Optional[str] = None

    @field_validator("university_code")
    @classmethod
    def code_must_be_alphanumeric(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.replace("-", "").isalnum():
            raise ValueError(f"university_code không hợp lệ: {v!r}")
        if len(v) < 2 or len(v) > 20:
            raise ValueError(f"university_code phải từ 2–20 ký tự, nhận: {v!r}")
        return v

    @field_validator("university_type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"public", "private", "foreign_affiliated"}
        if v is not None and v not in allowed:
            raise ValueError(f"university_type phải là một trong {allowed}")
        return v

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"north", "central", "south"}
        if v is not None and v not in allowed:
            raise ValueError(f"region phải là một trong {allowed}")
        return v

    @field_validator("established_year")
    @classmethod
    def validate_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1800 <= v <= 2100):
            raise ValueError(f"established_year không hợp lệ: {v}")
        return v


class UniversityReadSchema(UniversityCreateSchema):
    """Schema đọc từ DB – bao gồm id và timestamps."""

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
