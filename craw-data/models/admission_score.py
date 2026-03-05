# ============================================================
# Model: AdmissionScore
# Bảng lưu điểm chuẩn lịch sử theo năm / trường / ngành
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from models.base import Base
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Danh sách phương thức xét tuyển hợp lệ
VALID_ADMISSION_METHODS = {"THPT", "hoc_ba", "DGNL", "SAT", "xet_tuyen_thang", "khac"}

# Danh sách tổ hợp môn chuẩn (theo Bộ GD&ĐT)
VALID_SUBJECT_COMBINATIONS = {
    "A00", "A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10",
    "B00", "B01", "B02", "B03", "B04", "B08",
    "C00", "C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08",
    "C14", "C15", "C16", "C17", "C19", "C20",
    "D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10",
    "D11", "D12", "D13", "D14", "D15",
    "D78", "D79", "D80", "D81", "D82", "D83", "D84", "D85", "D86",
    "X06", "X26", "KHAC",
}


class AdmissionScore(Base):
    """
    Điểm chuẩn xét tuyển của một ngành, tại một trường,
    trong một năm, theo một phương thức và tổ hợp môn cụ thể.
    """

    __tablename__ = "admission_scores"

    __table_args__ = (
        UniqueConstraint(
            "university_id", "major_id", "year", "admission_method", "subject_combination",
            name="uq_score_full_key",
        ),
        # Điểm chuẩn phải hợp lệ theo thang 100 (Hỗ trợ điểm kết hợp QSB)
        CheckConstraint(
            "cutoff_score IS NULL OR (cutoff_score >= 0.0 AND cutoff_score <= 100.0)",
            name="chk_cutoff_score_range",
        ),
        CheckConstraint("year >= 2018 AND year <= 2030", name="chk_year_range"),
        Index("idx_scores_year", "year"),
        Index("idx_scores_university_major", "university_id", "major_id"),
        Index("idx_scores_university_year", "university_id", "year"),
        {"schema": None},
    )

    # --- Primary Key ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # --- Foreign Keys ---
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    major_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("majors.id", ondelete="CASCADE"),
        nullable=False,
    )

    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    admission_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subject_combination: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cutoff_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Dùng BigInteger để tránh overflow từ rác dữ liệu crawl
    quota: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    # --- Relationships ---
    university: Mapped["University"] = relationship("University", back_populates="admission_scores", lazy="select")
    major: Mapped["Major"] = relationship("Major", back_populates="admission_scores", lazy="select")

    def __repr__(self) -> str:
        return f"<AdmissionScore uni={self.university_id} year={self.year} score={self.cutoff_score}>"


class AdmissionScoreCreate(BaseModel):
    university_id: uuid.UUID
    major_id: uuid.UUID
    year: int = Field(..., ge=2018, le=2030)
    admission_method: str = Field(default="THPT")
    subject_combination: str = Field(default="KHAC", max_length=10)
    cutoff_score: Optional[float] = Field(default=None)
    quota: Optional[int] = Field(default=None)
    note: Optional[str] = Field(default=None, max_length=1000)
    scraped_at: datetime
    source_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("admission_method")
    @classmethod
    def validate_admission_method(cls, v: str) -> str:
        v = v.strip()
        return v if v in VALID_ADMISSION_METHODS else "khac"

    @field_validator("subject_combination")
    @classmethod
    def validate_subject_combination(cls, v: str) -> str:
        v = v.strip().upper()
        return v if v in VALID_SUBJECT_COMBINATIONS else "KHAC"

    @field_validator("cutoff_score")
    @classmethod
    def validate_cutoff_score(cls, v: Optional[float]) -> Optional[float]:
        if v is None: return None
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"cutoff_score={v} ngoài khoảng [0, 100]")
        return round(v, 2)

    model_config = {"from_attributes": True}


class AdmissionScoreRead(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    major_id: uuid.UUID
    year: int
    admission_method: Optional[str]
    subject_combination: Optional[str]
    cutoff_score: Optional[float]
    quota: Optional[int]
    note: Optional[str]
    scraped_at: datetime
    source_url: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class AdmissionScoreRaw(BaseModel):
    university_code: str
    major_name_raw: str
    major_code: Optional[str] = None
    year: int
    admission_method: str = "THPT"
    subject_combination: str = "KHAC"
    cutoff_score: Optional[float] = None
    quota: Optional[int] = None
    note: Optional[str] = None
    scraped_at: datetime
    source_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_logic(self) -> "AdmissionScoreRaw":
        return self
