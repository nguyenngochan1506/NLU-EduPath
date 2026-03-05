"""Initial schema – universities, majors, admission_scores, crawl_logs

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

Bảng được tạo trong migration này:
  - universities      : Thông tin trường đại học (UUID PK)
  - majors            : Thông tin ngành học (UUID PK, JSONB fields)
  - admission_scores  : Điểm chuẩn lịch sử (UUID PK, composite UNIQUE key)
  - crawl_logs        : Nhật ký mỗi lần chạy spider (UUID PK)
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# ============================================================
# Revision identifiers – dùng bởi Alembic
# ============================================================
revision: str = "001"
down_revision: str | None = None  # Migration đầu tiên, không có cha
branch_labels: str | None = None
depends_on: str | None = None


# ============================================================
# UPGRADE – Tạo tất cả bảng
# ============================================================


def upgrade() -> None:
    """
    Tạo toàn bộ schema ban đầu:
      1. Bật extension pgcrypto (để dùng gen_random_uuid())
      2. Tạo bảng universities
      3. Tạo bảng majors
      4. Tạo bảng admission_scores
      5. Tạo bảng crawl_logs
      6. Tạo các index bổ sung
    """

    # ----------------------------------------------------------
    # 0. Bật pgcrypto extension (cần cho gen_random_uuid())
    # ----------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ----------------------------------------------------------
    # 1. Bảng universities
    # ----------------------------------------------------------
    op.create_table(
        "universities",
        # Primary Key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            comment="UUID khóa chính – sinh tự động phía Python",
        ),
        # Business Key
        sa.Column(
            "university_code",
            sa.String(20),
            nullable=False,
            comment="Mã trường do Bộ GD&ĐT cấp (VD: QSB, BKA)",
        ),
        # Tên
        sa.Column(
            "name",
            sa.String(300),
            nullable=False,
            comment="Tên đầy đủ",
        ),
        sa.Column(
            "short_name",
            sa.String(50),
            nullable=True,
            comment="Tên viết tắt (VD: HUST, UEH)",
        ),
        # Phân loại
        sa.Column(
            "university_type",
            sa.String(25),
            nullable=True,
            comment="public | private | foreign_affiliated",
        ),
        sa.Column(
            "region",
            sa.String(10),
            nullable=True,
            comment="north | central | south",
        ),
        sa.Column(
            "province",
            sa.String(100),
            nullable=True,
        ),
        sa.Column("address", sa.Text(), nullable=True),
        # Web
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("admission_url", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        # Tuyển sinh
        sa.Column(
            "tuition_min",
            sa.BigInteger(),
            nullable=True,
            comment="Học phí thấp nhất VNĐ/năm",
        ),
        sa.Column(
            "tuition_max",
            sa.BigInteger(),
            nullable=True,
            comment="Học phí cao nhất VNĐ/năm",
        ),
        sa.Column("established_year", sa.SmallInteger(), nullable=True),
        # Trạng thái
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Crawl metadata
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Thời điểm thu thập dữ liệu",
        ),
        sa.Column(
            "source_url", sa.String(500), nullable=True, comment="URL trang đã crawl"
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Unique constraint và indexes cho universities
    op.create_unique_constraint(
        "uq_universities_code", "universities", ["university_code"]
    )
    op.create_index("idx_universities_code", "universities", ["university_code"])
    op.create_index("idx_universities_region", "universities", ["region"])
    op.create_index("idx_universities_province", "universities", ["province"])
    op.create_index("idx_universities_is_active", "universities", ["is_active"])

    # ----------------------------------------------------------
    # 2. Bảng majors
    # ----------------------------------------------------------
    op.create_table(
        "majors",
        # Primary Key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            comment="UUID v4 – sinh tự động",
        ),
        # Business Key
        sa.Column(
            "major_code",
            sa.String(20),
            nullable=False,
            comment="Mã ngành chuẩn 7 chữ số do Bộ GD&ĐT cấp, VD: 7480201",
        ),
        sa.Column(
            "name",
            sa.String(300),
            nullable=False,
            comment="Tên ngành học",
        ),
        # Khối ngành
        sa.Column(
            "major_group",
            sa.String(100),
            nullable=True,
            comment="Tên khối ngành, VD: Kỹ thuật và Công nghệ",
        ),
        sa.Column(
            "major_group_code",
            sa.String(10),
            nullable=True,
            comment="Mã khối ngành, VD: 7480",
        ),
        # Mô tả
        sa.Column("description", sa.Text(), nullable=True),
        # JSONB lists
        sa.Column(
            "career_options",
            JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Danh sách nghề nghiệp, VD: ["Lập trình viên", "BA"]',
        ),
        sa.Column(
            "required_skills",
            JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Kỹ năng yêu cầu, VD: ["Python", "Toán cao cấp"]',
        ),
        sa.Column(
            "subject_combinations",
            JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Tổ hợp môn xét tuyển, VD: ["A00", "A01", "D01"]',
        ),
        # Holland RIASEC & Career Anchors
        sa.Column(
            "holland_types",
            JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment='Holland types, VD: ["I", "R"]',
        ),
        sa.Column(
            "career_anchor_tags",
            JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="Career Anchor tags",
        ),
        # Đào tạo
        sa.Column(
            "study_duration",
            sa.SmallInteger(),
            nullable=True,
            server_default="4",
            comment="Thời gian đào tạo (năm)",
        ),
        sa.Column(
            "degree_level",
            sa.String(20),
            nullable=True,
            server_default=sa.text("'bachelor'"),
            comment="bachelor | engineer | master",
        ),
        # Trạng thái
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="False = ngành đã bị xóa hoặc không còn tuyển sinh",
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True = Admin đã review và approve holland_types cho AI",
        ),
        # Crawl metadata
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Thời điểm thu thập từ web",
        ),
        sa.Column("source_url", sa.String(500), nullable=True),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Unique constraint và indexes cho majors
    op.create_unique_constraint("uq_majors_code", "majors", ["major_code"])
    op.create_index("idx_majors_code", "majors", ["major_code"])
    op.create_index("idx_majors_group_code", "majors", ["major_group_code"])
    op.create_index("idx_majors_is_active", "majors", ["is_active"])
    op.create_index("idx_majors_is_published", "majors", ["is_published"])

    # GIN index cho JSONB fields (để query nhanh theo array elements)
    op.execute(
        "CREATE INDEX idx_majors_holland_types ON majors USING GIN (holland_types)"
    )
    op.execute(
        "CREATE INDEX idx_majors_subject_combinations ON majors USING GIN (subject_combinations)"
    )
    op.execute(
        "CREATE INDEX idx_majors_career_anchor_tags ON majors USING GIN (career_anchor_tags)"
    )

    # ----------------------------------------------------------
    # 3. Bảng admission_scores
    # ----------------------------------------------------------
    op.create_table(
        "admission_scores",
        # Primary Key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Foreign Keys
        sa.Column(
            "university_id",
            UUID(as_uuid=True),
            sa.ForeignKey("universities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "major_id",
            UUID(as_uuid=True),
            sa.ForeignKey("majors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Năm tuyển sinh
        sa.Column("year", sa.SmallInteger(), nullable=False),
        # Phương thức xét tuyển
        sa.Column(
            "admission_method",
            sa.String(100),
            nullable=True,
            comment="THPT | hoc_ba | DGNL | SAT | xet_tuyen_thang | khac",
        ),
        # Tổ hợp môn
        sa.Column(
            "subject_combination",
            sa.String(10),
            nullable=True,
            comment="Mã tổ hợp chuẩn, VD: A00, D01",
        ),
        # Điểm chuẩn
        sa.Column(
            "cutoff_score",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Điểm chuẩn thang 30",
        ),
        # Chỉ tiêu
        sa.Column("quota", sa.Integer(), nullable=True),
        # Ghi chú
        sa.Column("note", sa.Text(), nullable=True),
        # Crawl metadata
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Constraints
        sa.UniqueConstraint(
            "university_id",
            "major_id",
            "year",
            "admission_method",
            "subject_combination",
            name="uq_score_full_key",
        ),
        sa.CheckConstraint(
            "cutoff_score IS NULL OR (cutoff_score >= 10.0 AND cutoff_score <= 30.0)",
            name="chk_cutoff_score_range",
        ),
        sa.CheckConstraint(
            "year >= 2018 AND year <= 2030",
            name="chk_year_range",
        ),
    )

    # Indexes cho admission_scores
    op.create_index("idx_scores_year", "admission_scores", ["year"])
    op.create_index(
        "idx_scores_university_major",
        "admission_scores",
        ["university_id", "major_id"],
    )
    op.create_index(
        "idx_scores_university_year",
        "admission_scores",
        ["university_id", "year"],
    )
    op.create_index(
        "idx_scores_admission_method",
        "admission_scores",
        ["admission_method"],
    )

    # ----------------------------------------------------------
    # 4. Bảng crawl_logs
    # ----------------------------------------------------------
    op.create_table(
        "crawl_logs",
        # Primary Key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        # Spider info
        sa.Column("spider_name", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'running'"),
            comment="running | success | failed | partial",
        ),
        # Timestamps
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        # Counters
        sa.Column(
            "records_new",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "records_updated",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "records_failed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        # Error info
        sa.Column("error_summary", sa.Text(), nullable=True),
        # Trigger info
        sa.Column(
            "triggered_by",
            sa.String(100),
            nullable=True,
            comment="scheduler | admin:<user_uuid>",
        ),
    )

    # Indexes cho crawl_logs
    op.create_index("idx_crawl_logs_spider_name", "crawl_logs", ["spider_name"])
    op.create_index("idx_crawl_logs_status", "crawl_logs", ["status"])
    op.create_index("idx_crawl_logs_started_at", "crawl_logs", ["started_at"])

    # ----------------------------------------------------------
    # 5. Trigger: auto-update updated_at cho universities và majors
    # ----------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_universities_updated_at
        BEFORE UPDATE ON universities
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_majors_updated_at
        BEFORE UPDATE ON majors
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )


# ============================================================
# DOWNGRADE – Xóa tất cả bảng (rollback)
# ============================================================


def downgrade() -> None:
    """
    Rollback toàn bộ schema ban đầu.

    Xóa theo thứ tự ngược lại để tránh vi phạm FK constraint:
      1. crawl_logs
      2. admission_scores  (FK → universities, majors)
      3. majors
      4. universities
      5. Trigger function
    """

    # Xóa trigger trước
    op.execute("DROP TRIGGER IF EXISTS trg_majors_updated_at ON majors")
    op.execute("DROP TRIGGER IF EXISTS trg_universities_updated_at ON universities")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Xóa bảng theo thứ tự phụ thuộc FK
    op.drop_table("crawl_logs")
    op.drop_table("admission_scores")
    op.drop_table("majors")
    op.drop_table("universities")
