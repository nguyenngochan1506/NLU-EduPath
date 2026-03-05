# ============================================================
# db/repositories/score_repo.py
# Repository cho bảng admission_scores
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from models.admission_score import AdmissionScore, AdmissionScoreCreate
from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


class ScoreRepository:
    """
    Repository xử lý tất cả database operations cho bảng admission_scores.

    Pattern: Unit of Work – nhận session từ bên ngoài,
    không tự quản lý transaction (để pipeline kiểm soát).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ----------------------------------------------------------
    # READ
    # ----------------------------------------------------------

    def find_by_composite_key(
        self,
        university_id: uuid.UUID,
        major_id: uuid.UUID,
        year: int,
        admission_method: str,
        subject_combination: str,
    ) -> Optional[AdmissionScore]:
        """
        Tìm bản ghi theo composite key (dùng trong DeduplicationPipeline).
        Trả về None nếu chưa tồn tại.
        """
        stmt = select(AdmissionScore).where(
            and_(
                AdmissionScore.university_id == university_id,
                AdmissionScore.major_id == major_id,
                AdmissionScore.year == year,
                AdmissionScore.admission_method == admission_method,
                AdmissionScore.subject_combination == subject_combination,
            )
        )
        return self._session.scalar(stmt)

    def find_by_university_year(
        self,
        university_id: uuid.UUID,
        year: int,
    ) -> list[AdmissionScore]:
        """Lấy tất cả điểm chuẩn của một trường trong một năm."""
        stmt = select(AdmissionScore).where(
            and_(
                AdmissionScore.university_id == university_id,
                AdmissionScore.year == year,
            )
        )
        return list(self._session.scalars(stmt).all())

    def count_by_year(self, year: int) -> int:
        """Đếm số bản ghi theo năm (dùng trong data_quality_report)."""
        from sqlalchemy import func

        stmt = select(func.count()).where(AdmissionScore.year == year)
        return self._session.scalar(stmt) or 0

    def count_all(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(AdmissionScore)
        return self._session.scalar(stmt) or 0

    # ----------------------------------------------------------
    # WRITE
    # ----------------------------------------------------------

    def insert(self, schema: AdmissionScoreCreate) -> AdmissionScore:
        """
        INSERT một bản ghi mới.
        Caller phải đảm bảo bản ghi chưa tồn tại (dùng sau dedup check).
        """
        record = AdmissionScore(
            id=uuid.uuid4(),
            university_id=schema.university_id,
            major_id=schema.major_id,
            year=schema.year,
            admission_method=schema.admission_method,
            subject_combination=schema.subject_combination,
            cutoff_score=schema.cutoff_score,
            quota=schema.quota,
            note=schema.note,
            scraped_at=schema.scraped_at,
            source_url=schema.source_url,
        )
        self._session.add(record)
        return record

    def update_score(
        self,
        record_id: uuid.UUID,
        cutoff_score: Optional[float] = None,
        quota: Optional[int] = None,
        note: Optional[str] = None,
        scraped_at: Optional[datetime] = None,
        source_url: Optional[str] = None,
    ) -> int:
        """
        Cập nhật các cột giá trị của một bản ghi đã tồn tại.
        Trả về số hàng bị ảnh hưởng (0 hoặc 1).
        """
        values: dict = {}
        if cutoff_score is not None:
            values["cutoff_score"] = cutoff_score
        if quota is not None:
            values["quota"] = quota
        if note is not None:
            values["note"] = note
        if scraped_at is not None:
            values["scraped_at"] = scraped_at
        if source_url is not None:
            values["source_url"] = source_url

        if not values:
            return 0

        stmt = (
            update(AdmissionScore)
            .where(AdmissionScore.id == record_id)
            .values(**values)
        )
        result = self._session.execute(stmt)
        return result.rowcount

    def upsert(self, schema: AdmissionScoreCreate) -> tuple[AdmissionScore, bool]:
        """
        INSERT hoặc UPDATE dựa trên composite key.

        Returns:
            (record, created)
            created = True  → bản ghi mới được tạo
            created = False → bản ghi cũ được cập nhật (nếu có thay đổi)
                              hoặc giữ nguyên (nếu không đổi)
        """
        existing = self.find_by_composite_key(
            university_id=schema.university_id,
            major_id=schema.major_id,
            year=schema.year,
            admission_method=schema.admission_method,
            subject_combination=schema.subject_combination,
        )

        if existing is None:
            record = self.insert(schema)
            return record, True

        # Kiểm tra xem có thay đổi không trước khi update
        changed = (
            existing.cutoff_score != schema.cutoff_score
            or existing.quota != schema.quota
            or existing.note != schema.note
        )

        if changed:
            self.update_score(
                record_id=existing.id,
                cutoff_score=schema.cutoff_score,
                quota=schema.quota,
                note=schema.note,
                scraped_at=schema.scraped_at,
                source_url=schema.source_url,
            )
            # Refresh object để lấy giá trị mới nhất
            self._session.refresh(existing)

        return existing, False

    def bulk_upsert_pg(self, schemas: list[AdmissionScoreCreate]) -> dict[str, int]:
        """
        Bulk upsert dùng PostgreSQL ON CONFLICT DO UPDATE.
        Hiệu quả hơn khi insert số lượng lớn (hàng trăm bản ghi cùng lúc).

        Returns:
            {"inserted": n, "updated": m}
        """
        if not schemas:
            return {"inserted": 0, "updated": 0}

        rows = [
            {
                "id": uuid.uuid4(),
                "university_id": s.university_id,
                "major_id": s.major_id,
                "year": s.year,
                "admission_method": s.admission_method,
                "subject_combination": s.subject_combination,
                "cutoff_score": s.cutoff_score,
                "quota": s.quota,
                "note": s.note,
                "scraped_at": s.scraped_at,
                "source_url": s.source_url,
            }
            for s in schemas
        ]

        stmt = pg_insert(AdmissionScore).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_score_full_key",
            set_={
                "cutoff_score": stmt.excluded.cutoff_score,
                "quota": stmt.excluded.quota,
                "note": stmt.excluded.note,
                "scraped_at": stmt.excluded.scraped_at,
                "source_url": stmt.excluded.source_url,
            },
        )

        result = self._session.execute(stmt)
        # rowcount trong ON CONFLICT UPDATE = rows inserted + rows updated
        return {"inserted": result.rowcount, "updated": 0}

    def delete_by_id(self, record_id: uuid.UUID) -> bool:
        """Xóa một bản ghi theo id. Trả về True nếu xóa thành công."""
        record = self._session.get(AdmissionScore, record_id)
        if record is None:
            return False
        self._session.delete(record)
        return True
