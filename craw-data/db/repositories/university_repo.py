# ============================================================
# db/repositories/university_repo.py
# Repository pattern cho bảng universities
# ============================================================

from __future__ import annotations

import uuid
from typing import Optional

from models.university import University, UniversityCreateSchema
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


class UniversityRepository:
    """
    Tất cả thao tác DB liên quan đến bảng `universities`.

    Dùng repository pattern để tách biệt logic truy vấn DB
    khỏi pipeline và spider.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ----------------------------------------------------------
    # READ
    # ----------------------------------------------------------

    def get_by_id(self, university_id: uuid.UUID) -> Optional[University]:
        """Lấy trường theo UUID primary key."""
        return self._session.get(University, university_id)

    def get_by_code(self, university_code: str) -> Optional[University]:
        """
        Lấy trường theo mã Bộ GD&ĐT (business key).
        Đây là method được dùng nhiều nhất để resolve FK.
        """
        stmt = select(University).where(
            University.university_code == university_code.strip().upper()
        )
        return self._session.scalar(stmt)

    def get_all_active(self) -> list[University]:
        """Lấy tất cả trường đang hoạt động (is_active=True)."""
        stmt = select(University).where(University.is_active.is_(True))
        return list(self._session.scalars(stmt).all())

    def get_all_codes(self) -> list[str]:
        """Trả về danh sách tất cả university_code trong DB."""
        from sqlalchemy import distinct

        stmt = select(distinct(University.university_code)).where(
            University.is_active.is_(True)
        )
        return list(self._session.scalars(stmt).all())

    def exists(self, university_code: str) -> bool:
        """Kiểm tra trường đã tồn tại trong DB chưa."""
        from sqlalchemy import exists as sa_exists

        stmt = select(
            sa_exists().where(
                University.university_code == university_code.strip().upper()
            )
        )
        return bool(self._session.scalar(stmt))

    # ----------------------------------------------------------
    # WRITE
    # ----------------------------------------------------------

    def create(self, data: UniversityCreateSchema) -> University:
        """
        Tạo mới một bản ghi university.
        ID (UUID) được sinh tự động phía Python.
        """
        university = University(
            id=uuid.uuid4(),
            **data.model_dump(exclude_none=False),
        )
        self._session.add(university)
        self._session.flush()  # Flush để lấy id trước khi commit
        return university

    def update(
        self,
        university_code: str,
        updates: dict,
    ) -> Optional[University]:
        """
        Cập nhật một university theo code.
        Trả về None nếu không tìm thấy.
        """
        university = self.get_by_code(university_code)
        if university is None:
            return None

        for key, value in updates.items():
            if hasattr(university, key) and value is not None:
                setattr(university, key, value)

        self._session.flush()
        return university

    def upsert(self, data: UniversityCreateSchema) -> tuple[University, bool]:
        """
        Insert nếu chưa tồn tại, Update nếu đã tồn tại.

        Returns:
            (university, created)  –  created=True nếu INSERT, False nếu UPDATE
        """
        existing = self.get_by_code(data.university_code)

        if existing is None:
            new_record = self.create(data)
            return new_record, True
        else:
            # Chỉ update các trường có giá trị mới (không None)
            updates = {
                k: v
                for k, v in data.model_dump().items()
                if v is not None and k != "university_code"
            }
            for key, value in updates.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            self._session.flush()
            return existing, False

    def bulk_upsert(self, records: list[UniversityCreateSchema]) -> tuple[int, int]:
        """
        Upsert nhiều bản ghi cùng lúc.

        Returns:
            (created_count, updated_count)
        """
        created = 0
        updated = 0
        for record in records:
            _, is_new = self.upsert(record)
            if is_new:
                created += 1
            else:
                updated += 1
        return created, updated

    def deactivate(self, university_code: str) -> bool:
        """Đánh dấu trường là không còn hoạt động (soft delete)."""
        university = self.get_by_code(university_code)
        if university is None:
            return False
        university.is_active = False
        self._session.flush()
        return True
