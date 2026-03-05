# ============================================================
# models/major.py – Major (Ngành học)
# SQLAlchemy ORM model + Pydantic validation schema
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from models.base import Base
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import Boolean, DateTime, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


# ============================================================
# SQLAlchemy Model
# ============================================================
class Major(Base):
    """
    Bảng lưu thông tin ngành học.
    PK: UUID – sinh tự động phía Python trước khi INSERT.

    Các cột JSONB (career_options, required_skills, v.v.) lưu danh sách
    string để dễ query và index bằng GIN.
    """

    __tablename__ = "majors"

    # --- Primary Key ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID v4 – sinh tự động",
    )

    # --- Định danh (business key) ---
    major_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Mã ngành chuẩn 7 chữ số do Bộ GD&ĐT cấp, VD: 7480201",
    )
    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Tên ngành học",
    )

    # --- Khối ngành ---
    major_group: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Tên khối ngành, VD: Kỹ thuật và Công nghệ",
    )
    major_group_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        comment="Mã khối ngành, VD: 7480",
    )

    # --- Mô tả ---
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Mô tả ngành học, cơ hội việc làm, v.v.",
    )

    # --- JSONB lists ---
    career_options: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="'[]'::jsonb",
        comment='Danh sách nghề nghiệp, VD: ["Lập trình viên", "BA"]',
    )
    required_skills: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="'[]'::jsonb",
        comment='Kỹ năng yêu cầu, VD: ["Python", "Toán cao cấp"]',
    )
    subject_combinations: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="'[]'::jsonb",
        comment='Tổ hợp môn xét tuyển, VD: ["A00", "A01", "D01"]',
    )

    # --- Holland RIASEC & Career Anchors (dùng cho AI engine) ---
    holland_types: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="'[]'::jsonb",
        comment='Holland types, VD: ["I", "R"] – xem Phụ lục C trong docs',
    )
    career_anchor_tags: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        server_default="'[]'::jsonb",
        comment='Career Anchor tags, VD: ["Technical/Functional Competence"]',
    )

    # --- Đào tạo ---
    study_duration: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        server_default="4",
        comment="Thời gian đào tạo (năm)",
    )
    degree_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        server_default="'bachelor'",
        comment="bachelor | engineer | master",
    )

    # --- Trạng thái ---
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="False = ngành đã bị xóa hoặc không còn tuyển sinh",
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="True = Admin đã review và approve holland_types cho AI",
    )

    # --- Crawl metadata ---
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Thời điểm thu thập từ web",
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL trang nguồn đã crawl",
    )

    # --- Audit ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --- Relationships ---
    admission_scores: Mapped[list["AdmissionScore"]] = relationship(  # noqa: F821
        "AdmissionScore", back_populates="major", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Major code={self.major_code!r} name={self.name!r}>"


# ============================================================
# Pydantic Schemas  (dùng trong ValidationPipeline)
# ============================================================
class MajorCreate(BaseModel):
    """Schema validate item từ MajorInfoSpider trước khi INSERT."""

    major_code: str = Field(
        ...,
        pattern=r"^(\d{7}|AUTO-[A-Z0-9]{6})$",
        description="Mã ngành 7 chữ số hoặc mã tự sinh AUTO-XXXXXX",
    )
    name: str = Field(..., min_length=2, max_length=300)
    major_group: Optional[str] = Field(None, max_length=100)
    major_group_code: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    career_options: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    subject_combinations: list[str] = Field(default_factory=list)
    holland_types: list[str] = Field(default_factory=list)
    career_anchor_tags: list[str] = Field(default_factory=list)
    study_duration: Optional[int] = Field(None, ge=1, le=10)
    degree_level: Optional[str] = Field(
        None,
        pattern=r"^(bachelor|engineer|master)$",
    )
    scraped_at: datetime
    source_url: Optional[str] = None

    @field_validator("holland_types")
    @classmethod
    def validate_holland_types(cls, v: list[str]) -> list[str]:
        allowed = {"R", "I", "A", "S", "E", "C"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Holland types không hợp lệ: {invalid}")
        return v

    @field_validator("subject_combinations")
    @classmethod
    def validate_subject_combinations(cls, v: list[str]) -> list[str]:
        allowed = {
            "A00",
            "A01",
            "A02",
            "A04",
            "A05",
            "A09",
            "A10",
            "A16",
            "B00",
            "B01",
            "B02",
            "B03",
            "B04",
            "B08",
            "C00",
            "C01",
            "C02",
            "C03",
            "C04",
            "C05",
            "C06",
            "C07",
            "C08",
            "D01",
            "D07",
            "D08",
            "D09",
            "D10",
            "X00",
            "X06",
            "X26",
        }
        invalid = set(v) - allowed
        if invalid:
            # Không raise – chỉ log warning, tổ hợp mới có thể xuất hiện
            pass
        return v


class MajorUpdate(BaseModel):
    """Schema để UPDATE một major đã tồn tại."""

    name: Optional[str] = Field(None, min_length=2, max_length=300)
    major_group: Optional[str] = None
    major_group_code: Optional[str] = None
    description: Optional[str] = None
    career_options: Optional[list[str]] = None
    required_skills: Optional[list[str]] = None
    subject_combinations: Optional[list[str]] = None
    holland_types: Optional[list[str]] = None
    career_anchor_tags: Optional[list[str]] = None
    study_duration: Optional[int] = None
    degree_level: Optional[str] = None
    is_active: Optional[bool] = None
    scraped_at: Optional[datetime] = None
    source_url: Optional[str] = None


class MajorRead(BaseModel):
    """Schema để trả về khi đọc từ DB (bao gồm id và timestamps)."""

    id: uuid.UUID
    major_code: str
    name: str
    major_group: Optional[str] = None
    major_group_code: Optional[str] = None
    description: Optional[str] = None
    career_options: list[str] = []
    required_skills: list[str] = []
    subject_combinations: list[str] = []
    holland_types: list[str] = []
    career_anchor_tags: list[str] = []
    study_duration: Optional[int] = None
    degree_level: Optional[str] = None
    is_active: bool
    is_published: bool
    scraped_at: datetime
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
