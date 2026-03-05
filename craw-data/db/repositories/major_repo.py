# ============================================================
# db/repositories/major_repo.py
# Repository pattern cho bảng majors
# ============================================================

from __future__ import annotations

import uuid
from typing import Optional

from models.major import Major, MajorCreate
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session


class MajorRepository:
    """
    Tất cả thao tác DB liên quan đến bảng `majors`.

    Dùng repository pattern để tách biệt logic truy vấn DB
    khỏi pipeline và spider.

    Quan trọng nhất: `resolve_major_id()` – dùng trong NormalizationPipeline
    để map major_name_raw → major_id (UUID).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

        # Cache nội bộ trong một session để tránh query lặp lại
        self._code_cache: dict[str, Major] = {}
        self._name_cache: dict[str, Major] = {}

    # ----------------------------------------------------------
    # READ
    # ----------------------------------------------------------

    def get_by_id(self, major_id: uuid.UUID) -> Optional[Major]:
        """Lấy ngành theo UUID primary key."""
        return self._session.get(Major, major_id)

    def get_by_code(self, major_code: str) -> Optional[Major]:
        """
        Lấy ngành theo mã Bộ GD&ĐT (business key).
        VD: "7480201" → Công nghệ thông tin

        Kết quả được cache trong session để tránh query lặp.
        """
        code = major_code.strip()
        if code in self._code_cache:
            return self._code_cache[code]

        stmt = select(Major).where(Major.major_code == code)
        result = self._session.scalar(stmt)

        if result:
            self._code_cache[code] = result
        return result

    def get_by_name_exact(self, name: str) -> Optional[Major]:
        """
        Tìm ngành theo tên chính xác (case-insensitive).
        Dùng khi NormalizationPipeline tìm theo tên đầy đủ.
        """
        name_normalized = name.strip()
        if name_normalized in self._name_cache:
            return self._name_cache[name_normalized]

        stmt = select(Major).where(
            func.lower(Major.name) == func.lower(name_normalized)
        )
        result = self._session.scalar(stmt)

        if result:
            self._name_cache[name_normalized] = result
        return result

    def search_by_name(self, keyword: str, limit: int = 5) -> list[Major]:
        """
        Tìm kiếm ngành theo từ khóa trong tên (ILIKE).
        Dùng làm fallback khi không match chính xác.

        Args:
            keyword: Từ khóa tìm kiếm (có thể là tên rút gọn)
            limit:   Số kết quả tối đa trả về

        Returns:
            Danh sách Major khớp, sắp xếp theo độ phù hợp (tên ngắn hơn trước)
        """
        pattern = f"%{keyword.strip()}%"
        stmt = (
            select(Major)
            .where(
                or_(
                    Major.name.ilike(pattern),
                    Major.major_code.ilike(pattern),
                )
            )
            .where(Major.is_active.is_(True))
            .order_by(func.length(Major.name))  # Ưu tiên tên ngắn (exact-like)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def get_all_active(self) -> list[Major]:
        """Lấy tất cả ngành đang hoạt động."""
        stmt = select(Major).where(Major.is_active.is_(True))
        return list(self._session.scalars(stmt).all())

    def get_all_codes(self) -> list[str]:
        """Trả về danh sách tất cả major_code trong DB."""
        from sqlalchemy import distinct

        stmt = select(distinct(Major.major_code)).where(Major.is_active.is_(True))
        return list(self._session.scalars(stmt).all())

    def get_code_to_id_map(self) -> dict[str, uuid.UUID]:
        """
        Trả về dict {major_code → uuid} cho tất cả ngành active.
        Dùng để bulk-resolve trong NormalizationPipeline khi crawl số lượng lớn.
        """
        stmt = select(Major.major_code, Major.id).where(Major.is_active.is_(True))
        rows = self._session.execute(stmt).all()
        return {row.major_code: row.id for row in rows}

    def get_name_to_id_map(self) -> dict[str, uuid.UUID]:
        """
        Trả về dict {lower(name) → uuid} cho tất cả ngành active.
        Dùng để tra cứu nhanh major_name_raw → id trong Normalization.
        """
        stmt = select(Major.name, Major.id).where(Major.is_active.is_(True))
        rows = self._session.execute(stmt).all()
        return {row.name.lower().strip(): row.id for row in rows}

    def exists(self, major_code: str) -> bool:
        """Kiểm tra ngành đã tồn tại trong DB chưa."""
        from sqlalchemy import exists as sa_exists

        stmt = select(sa_exists().where(Major.major_code == major_code.strip()))
        return bool(self._session.scalar(stmt))

    # ----------------------------------------------------------
    # RESOLVE (dùng trong NormalizationPipeline)
    # ----------------------------------------------------------

    def resolve_major_id(
        self,
        *,
        major_code: Optional[str] = None,
        major_name_raw: Optional[str] = None,
    ) -> Optional[uuid.UUID]:
        """
        Resolve major_code hoặc major_name_raw → UUID.

        Chiến lược (theo thứ tự ưu tiên):
        1. Nếu có `major_code` → tra theo mã chính xác
        2. Nếu không có mã, dùng `major_name_raw` → so khớp tên chính xác
        3. Fallback: tìm kiếm ILIKE theo từ khóa đầu tiên trong tên

        Returns:
            UUID của ngành nếu resolve thành công, None nếu không tìm thấy.
        """
        # Bước 1: Resolve theo mã ngành chuẩn
        if major_code:
            major = self.get_by_code(major_code.strip())
            if major:
                return major.id

        # Bước 2: Resolve theo tên đầy đủ (exact match)
        if major_name_raw:
            major = self.get_by_name_exact(major_name_raw.strip())
            if major:
                return major.id

            # Bước 3: Fallback – tìm kiếm theo từ khóa đầu tiên trong tên
            # (xử lý trường hợp tên có tiền tố như "Ngành Kỹ thuật phần mềm")
            keyword = _extract_keyword(major_name_raw)
            if keyword:
                candidates = self.search_by_name(keyword, limit=1)
                if candidates:
                    return candidates[0].id

        return None

    # ----------------------------------------------------------
    # WRITE
    # ----------------------------------------------------------

    def create(self, data: MajorCreate) -> Major:
        """
        Tạo mới một bản ghi major.
        ID (UUID) được sinh tự động phía Python.
        """
        major = Major(
            id=uuid.uuid4(),
            **data.model_dump(exclude_none=False),
        )
        self._session.add(major)
        self._session.flush()  # Flush để lấy id trước khi commit
        return major

    def update(self, major_code: str, updates: dict) -> Optional[Major]:
        """
        Cập nhật một major theo code.
        Trả về None nếu không tìm thấy.
        """
        major = self.get_by_code(major_code)
        if major is None:
            return None

        for key, value in updates.items():
            if hasattr(major, key) and value is not None:
                setattr(major, key, value)

        self._session.flush()
        # Xóa cache sau update
        self._code_cache.pop(major_code.strip(), None)
        self._name_cache.clear()
        return major

    def upsert(self, data: MajorCreate) -> tuple[Major, bool]:
        """
        Insert nếu chưa tồn tại, Update nếu đã tồn tại.

        Returns:
            (major, created)  –  created=True nếu INSERT, False nếu UPDATE
        """
        existing = self.get_by_code(data.major_code)

        if existing is None:
            new_record = self.create(data)
            return new_record, True

        # Chỉ update các trường có giá trị mới (không None)
        updates = {
            k: v
            for k, v in data.model_dump().items()
            if v is not None and k != "major_code"
        }
        for key, value in updates.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        self._session.flush()
        # Xóa cache
        self._code_cache.pop(data.major_code.strip(), None)
        self._name_cache.clear()
        return existing, False

    def bulk_upsert(self, records: list[MajorCreate]) -> tuple[int, int]:
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

    def clear_cache(self) -> None:
        """Xóa toàn bộ cache nội bộ (dùng khi seed data thay đổi)."""
        self._code_cache.clear()
        self._name_cache.clear()


# ----------------------------------------------------------
# Helpers (module-level, không phải method)
# ----------------------------------------------------------


def _extract_keyword(major_name_raw: str) -> Optional[str]:
    """
    Trích xuất từ khóa có ý nghĩa nhất từ tên ngành thô.

    Bỏ qua các prefix phổ biến như:
        "Ngành", "Chuyên ngành", "Khoa", "Bộ môn"
    và lấy phần còn lại làm keyword.

    VD:
        "Ngành Kỹ thuật phần mềm"  → "Kỹ thuật phần mềm"
        "Kỹ thuật phần mềm (KTPM)" → "Kỹ thuật phần mềm"
        "CNTT"                      → "CNTT"

    Returns:
        Keyword đã làm sạch, hoặc None nếu không extract được.
    """
    import re

    if not major_name_raw:
        return None

    # Bỏ nội dung trong ngoặc đơn/kép ở cuối (VD: "(KTPM)", "[Chất lượng cao]")
    cleaned = re.sub(r"[\(\[（【][^\)\]）】]*[\)\]）】]", "", major_name_raw)

    # Bỏ prefix
    prefixes = [
        r"^ngành\s+",
        r"^chuyên ngành\s+",
        r"^khoa\s+(?!học\b)",
        r"^bộ môn\s+",
        r"^chương trình\s+",
        r"^hệ\s+",
    ]

    for prefix in prefixes:
        cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()
    return cleaned if cleaned else None
