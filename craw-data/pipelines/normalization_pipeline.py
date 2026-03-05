# ============================================================
# pipelines/normalization_pipeline.py
# Pipeline 2 (priority 200): Chuẩn hóa dữ liệu sau khi validate
#
# Nhiệm vụ:
#   - Chuẩn hóa tên ngành thô (major_name_raw) → tên chuẩn
#   - Map tên ngành → major_code (mã 7 chữ số Bộ GD&ĐT) nếu có thể
#   - Chuẩn hóa tổ hợp môn (subject_combination) → mã chuẩn (A00, D01, ...)
#   - Chuẩn hóa mã trường (university_code) → uppercase, strip
#   - Chuẩn hóa điểm số (string → float) và chỉ tiêu (string → int)
#   - Chuẩn hóa admission_method → giá trị enum hợp lệ
#   - Trim / clean tất cả các trường string
#
# Items được xử lý:
#   AdmissionScoreItem → chuẩn hóa toàn bộ các trường
#   UniversityItem     → chuẩn hóa code, name, url
#   MajorItem          → chuẩn hóa name, subject_combinations
# ============================================================

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from itemadapter import ItemAdapter
from scrapy import Spider
from utils.major_code_mapper import MajorCodeMapper

logger = logging.getLogger(__name__)

# Mapping admission_method từ dạng tự nhiên → giá trị enum chuẩn
_ADMISSION_METHOD_MAP: dict[str, str] = {
    # THPT – Thi tốt nghiệp THPT
    "thpt": "THPT",
    "thi thpt": "THPT",
    "điểm thi thpt": "THPT",
    "diem thi thpt": "THPT",
    "thi tốt nghiệp": "THPT",
    "tot nghiep thpt": "THPT",
    "xét điểm thi thpt": "THPT",
    "xet diem thi thpt": "THPT",
    # hoc_ba – Xét học bạ
    "hoc_ba": "hoc_ba",
    "học bạ": "hoc_ba",
    "hoc ba": "hoc_ba",
    "xét học bạ": "hoc_ba",
    "xet hoc ba": "hoc_ba",
    "điểm học bạ": "hoc_ba",
    "diem hoc ba": "hoc_ba",
    "học bạ thpt": "hoc_ba",
    # DGNL – Đánh giá năng lực
    "DGNL": "DGNL",
    "dgnl": "DGNL",
    "đánh giá năng lực": "DGNL",
    "danh gia nang luc": "DGNL",
    "đgnl": "DGNL",
    "bài thi đánh giá năng lực": "DGNL",
    "thi đánh giá năng lực": "DGNL",
    "đgnl đhqg tphcm": "DGNL",
    "đgnl đhqg hà nội": "DGNL",
    # SAT – Chứng chỉ quốc tế
    "sat": "SAT",
    "SAT": "SAT",
    "ielts": "SAT",
    "toefl": "SAT",
    "chứng chỉ quốc tế": "SAT",
    "chung chi quoc te": "SAT",
    # xet_tuyen_thang – Xét tuyển thẳng
    "xet_tuyen_thang": "xet_tuyen_thang",
    "xét tuyển thẳng": "xet_tuyen_thang",
    "xet tuyen thang": "xet_tuyen_thang",
    "tuyển thẳng": "xet_tuyen_thang",
    "tuyen thang": "xet_tuyen_thang",
    "ưu tiên xét tuyển": "xet_tuyen_thang",
    # khac – Các phương thức khác
    "khac": "khac",
    "khác": "khac",
    "other": "khac",
    "phương thức khác": "khac",
}

# Giá trị hợp lệ cho admission_method
_VALID_ADMISSION_METHODS = {"THPT", "hoc_ba", "DGNL", "SAT", "xet_tuyen_thang", "khac"}


class NormalizationPipeline:
    """
    Pipeline thứ hai trong chuỗi xử lý (priority=200).

    Nhận item đã được ValidationPipeline kiểm tra và chuẩn hóa
    các giá trị để đảm bảo tính nhất quán trước khi dedup và lưu.

    Thống kê:
        - items_normalized       : Số item đã chuẩn hóa thành công
        - major_code_resolved    : Số lần resolve major_code thành công
        - major_code_unresolved  : Số lần không resolve được (fallback None)
        - subject_combo_resolved : Số lần normalize tổ hợp môn thành công
    """

    def __init__(self) -> None:
        self.items_normalized = 0
        self.major_code_resolved = 0
        self.major_code_unresolved = 0
        self.subject_combo_resolved = 0

        # MajorCodeMapper được khởi tạo một lần khi spider mở
        self._major_mapper: Any = None

    # ----------------------------------------------------------
    # Scrapy hooks
    # ----------------------------------------------------------

    def open_spider(self, spider: Spider) -> None:
        """Khởi tạo MajorCodeMapper khi spider bắt đầu."""
        self._major_mapper = MajorCodeMapper()
        logger.info(
            "[NormalizationPipeline] Spider '%s' bắt đầu. "
            "MajorCodeMapper đã load %d entries.",
            spider.name,
            len(self._major_mapper._lookup),
        )

    def close_spider(self, spider: Spider) -> None:
        logger.info(
            "[NormalizationPipeline] Spider '%s' kết thúc. "
            "Đã chuẩn hóa=%d | major_code resolved=%d | unresolved=%d | "
            "subject_combo resolved=%d",
            spider.name,
            self.items_normalized,
            self.major_code_resolved,
            self.major_code_unresolved,
            self.subject_combo_resolved,
        )

    def process_item(self, item: Any, spider: Spider) -> Any:
        """
        Điều phối chuẩn hóa theo loại item.
        Luôn trả về item (pipeline này không bao giờ drop item).
        """
        adapter = ItemAdapter(item)
        item_type = type(item).__name__

        if item_type == "AdmissionScoreItem":
            self._normalize_admission_score(adapter, spider)
            # Sau khi chuẩn hóa, thử resolve IDs luôn để phục vụ DeduplicationPipeline
            self._resolve_ids_for_score(adapter)
        elif item_type == "UniversityItem":
            self._normalize_university(adapter, spider)
        elif item_type == "MajorItem":
            self._normalize_major(adapter, spider)
        else:
            logger.debug(
                "[NormalizationPipeline] Item type không biết: %s – bỏ qua.", item_type
            )
            return item

        self.items_normalized += 1
        return item

    def _resolve_ids_for_score(self, adapter: ItemAdapter) -> None:
        """Thử resolve university_id và major_id ngay tại đây."""
        university_code = adapter.get("university_code")
        major_code = adapter.get("major_code")
        major_name_raw = adapter.get("major_name_raw")

        # Resolve university_id
        if university_code:
            from db.connection import get_session
            from db.repositories.university_repo import UniversityRepository
            with get_session() as session:
                repo = UniversityRepository(session)
                uni = repo.get_by_code(university_code)
                if uni:
                    adapter["_university_id"] = uni.id

        # Resolve major_id
        if major_code or major_name_raw:
            from db.connection import get_session
            from db.repositories.major_repo import MajorRepository
            with get_session() as session:
                repo = MajorRepository(session)
                major_id = repo.resolve_major_id(
                    major_code=major_code, major_name_raw=major_name_raw
                )
                if major_id:
                    adapter["_major_id"] = major_id

    # ----------------------------------------------------------
    # Normalize theo loại item
    # ----------------------------------------------------------

    def _normalize_admission_score(self, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Chuẩn hóa AdmissionScoreItem.

        Thứ tự xử lý:
        1. university_code → uppercase, strip
        2. major_name_raw → clean text
        3. major_code → map từ major_name_raw nếu chưa có
        4. year → int
        5. admission_method → map sang enum chuẩn
        6. subject_combination → normalize sang mã chuẩn (A00, D01, ...)
        7. cutoff_score → float (đã validate ở pipeline trước, chỉ round)
        8. quota → int
        9. note → strip
        10. source_url → strip
        """
        from utils.text_normalizer import (
            normalize_major_name,
            normalize_quota,
            normalize_score,
            normalize_subject_combo,
            normalize_university_code,
        )

        # 1. university_code
        raw_code = adapter.get("university_code") or ""
        adapter["university_code"] = normalize_university_code(str(raw_code))

        # 2. major_name_raw – làm sạch text nhưng giữ nguyên ngữ nghĩa
        raw_major_name = adapter.get("major_name_raw") or ""
        cleaned_major_name = normalize_major_name(str(raw_major_name))
        adapter["major_name_raw"] = cleaned_major_name

        # 3. major_code – resolve từ tên nếu chưa có
        existing_code = adapter.get("major_code")
        if not existing_code and cleaned_major_name and self._major_mapper:
            resolved_code = self._major_mapper.get_code(cleaned_major_name)
            if resolved_code:
                adapter["major_code"] = resolved_code
                self.major_code_resolved += 1
                logger.debug(
                    "[NormalizationPipeline] Resolved major_code: %r → %s",
                    cleaned_major_name,
                    resolved_code,
                )
            else:
                adapter["major_code"] = None
                self.major_code_unresolved += 1
                logger.debug(
                    "[NormalizationPipeline] Không resolve được major_code: %r",
                    cleaned_major_name,
                )
        elif existing_code:
            # Đã có code – chỉ strip
            adapter["major_code"] = str(existing_code).strip()

        # 4. year → đảm bảo int
        year_raw = adapter.get("year")
        if year_raw is not None:
            try:
                adapter["year"] = int(year_raw)
            except (TypeError, ValueError):
                pass  # Đã validate ở pipeline trước

        # 5. admission_method → normalize sang enum
        admission_method_raw = adapter.get("admission_method") or "THPT"
        adapter["admission_method"] = _normalize_admission_method(
            str(admission_method_raw)
        )

        # 6. subject_combination → mã chuẩn
        combo_raw = adapter.get("subject_combination") or ""
        if combo_raw and str(combo_raw).strip():
            normalized_combo = normalize_subject_combo(str(combo_raw))
            adapter["subject_combination"] = normalized_combo
            if normalized_combo != "KHAC":
                self.subject_combo_resolved += 1
        else:
            adapter["subject_combination"] = "KHAC"

        # 7. cutoff_score → normalize (có thể chưa được parse ở validation)
        cutoff_raw = adapter.get("cutoff_score")
        if cutoff_raw is not None:
            normalized_score = normalize_score(cutoff_raw)
            adapter["cutoff_score"] = normalized_score
        # else: giữ None

        # 8. quota → normalize
        quota_raw = adapter.get("quota")
        adapter["quota"] = normalize_quota(quota_raw)

        # 9. note → strip và xóa nếu rỗng
        note_raw = adapter.get("note")
        if note_raw:
            note_stripped = _clean_text_field(str(note_raw), max_length=500)
            adapter["note"] = note_stripped if note_stripped else None
        else:
            adapter["note"] = None

        # 10. source_url → strip
        url_raw = adapter.get("source_url")
        if url_raw:
            adapter["source_url"] = str(url_raw).strip()[:500]

    def _normalize_university(self, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Chuẩn hóa UniversityItem.

        Thứ tự xử lý:
        1. university_code → uppercase, strip
        2. name → clean, title case nếu cần
        3. short_name → uppercase nếu là viết tắt thuần ASCII
        4. university_type → lowercase, validate
        5. region → lowercase, validate
        6. province → strip
        7. address → strip
        8. URLs → strip
        9. tuition_min/max → int
        10. established_year → int
        """
        from utils.text_normalizer import normalize_university_code

        # 1. university_code
        raw_code = adapter.get("university_code") or ""
        adapter["university_code"] = normalize_university_code(str(raw_code))

        # 2. name
        raw_name = adapter.get("name") or ""
        adapter["name"] = _clean_text_field(str(raw_name), max_length=300)

        # 3. short_name
        short_name_raw = adapter.get("short_name")
        if short_name_raw:
            short_name = str(short_name_raw).strip()
            # Nếu toàn ASCII thì uppercase (VD: "hust" → "HUST")
            if short_name.isascii() and short_name.isalpha():
                short_name = short_name.upper()
            adapter["short_name"] = short_name[:50] if short_name else None

        # 4. university_type
        uni_type_raw = adapter.get("university_type")
        if uni_type_raw:
            uni_type = str(uni_type_raw).strip().lower()
            type_map = {
                "công lập": "public",
                "cong lap": "public",
                "public": "public",
                "tư thục": "private",
                "tu thuc": "private",
                "private": "private",
                "dân lập": "private",
                "dan lap": "private",
                "liên kết nước ngoài": "foreign_affiliated",
                "foreign": "foreign_affiliated",
                "foreign_affiliated": "foreign_affiliated",
                "nước ngoài": "foreign_affiliated",
            }
            adapter["university_type"] = type_map.get(uni_type, None)

        # 5. region
        region_raw = adapter.get("region")
        if region_raw:
            region = str(region_raw).strip().lower()
            region_map = {
                "north": "north",
                "bắc": "north",
                "miền bắc": "north",
                "mien bac": "north",
                "hà nội": "north",
                "central": "central",
                "trung": "central",
                "miền trung": "central",
                "mien trung": "central",
                "đà nẵng": "central",
                "south": "south",
                "nam": "south",
                "miền nam": "south",
                "mien nam": "south",
                "hồ chí minh": "south",
                "tp.hcm": "south",
                "tphcm": "south",
            }
            adapter["region"] = region_map.get(region, None)

        # 6-7. province, address
        for field in ("province", "address"):
            val = adapter.get(field)
            if val:
                adapter[field] = _clean_text_field(str(val), max_length=200)

        # 8. URLs – chỉ strip
        for url_field in ("website", "admission_url", "logo_url", "source_url"):
            val = adapter.get(url_field)
            if val:
                adapter[url_field] = str(val).strip()[:500]

        # 9. tuition
        for fee_field in ("tuition_min", "tuition_max"):
            val = adapter.get(fee_field)
            if val is not None:
                try:
                    adapter[fee_field] = int(val)
                except (TypeError, ValueError):
                    adapter[fee_field] = None

        # 10. established_year
        year_raw = adapter.get("established_year")
        if year_raw is not None:
            try:
                adapter["established_year"] = int(year_raw)
            except (TypeError, ValueError):
                adapter["established_year"] = None

    def _normalize_major(self, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Chuẩn hóa MajorItem.

        Thứ tự xử lý:
        1. major_code → strip (đã validate 7 chữ số ở pipeline trước)
        2. name → clean text
        3. major_group, major_group_code → strip
        4. description → clean text
        5. subject_combinations → normalize mỗi combo sang mã chuẩn
        6. holland_types → uppercase, dedup
        7. career_anchor_tags → strip, dedup
        8. career_options, required_skills → strip, dedup
        9. study_duration → int
        10. degree_level → lowercase, validate
        """
        from utils.text_normalizer import normalize_major_name, normalize_subject_combo

        # 1. major_code
        raw_code = adapter.get("major_code") or ""
        adapter["major_code"] = str(raw_code).strip()

        # 2. name
        raw_name = adapter.get("name") or ""
        adapter["name"] = normalize_major_name(str(raw_name)) or str(raw_name).strip()

        # 3. major_group, major_group_code
        for field in ("major_group", "major_group_code"):
            val = adapter.get(field)
            if val:
                adapter[field] = str(val).strip()

        # 4. description
        desc_raw = adapter.get("description")
        if desc_raw:
            adapter["description"] = _clean_text_field(str(desc_raw))

        # 5. subject_combinations – normalize từng combo
        combos_raw = adapter.get("subject_combinations") or []
        if isinstance(combos_raw, list):
            normalized_combos = []
            seen = set()
            for combo in combos_raw:
                if not combo:
                    continue
                norm = normalize_subject_combo(str(combo))
                if norm not in seen:
                    normalized_combos.append(norm)
                    seen.add(norm)
                    if norm != "KHAC":
                        self.subject_combo_resolved += 1
            adapter["subject_combinations"] = normalized_combos
        elif isinstance(combos_raw, str):
            from utils.text_normalizer import normalize_multiple_combos

            adapter["subject_combinations"] = normalize_multiple_combos(combos_raw)

        # 6. holland_types – uppercase, dedup, validate
        holland_raw = adapter.get("holland_types") or []
        if isinstance(holland_raw, list):
            valid_holland = {"R", "I", "A", "S", "E", "C"}
            normalized_holland = []
            seen = set()
            for h in holland_raw:
                h_upper = str(h).strip().upper()
                if h_upper in valid_holland and h_upper not in seen:
                    normalized_holland.append(h_upper)
                    seen.add(h_upper)
            adapter["holland_types"] = normalized_holland

        # 7. career_anchor_tags – strip, dedup
        tags_raw = adapter.get("career_anchor_tags") or []
        if isinstance(tags_raw, list):
            adapter["career_anchor_tags"] = _deduplicate_strings(tags_raw)

        # 8. career_options, required_skills – strip, dedup
        for list_field in ("career_options", "required_skills"):
            val = adapter.get(list_field) or []
            if isinstance(val, list):
                adapter[list_field] = _deduplicate_strings(val)

        # 9. study_duration
        duration_raw = adapter.get("study_duration")
        if duration_raw is not None:
            try:
                duration = int(duration_raw)
                adapter["study_duration"] = duration if 1 <= duration <= 10 else None
            except (TypeError, ValueError):
                adapter["study_duration"] = None

        # 10. degree_level
        degree_raw = adapter.get("degree_level")
        if degree_raw:
            degree = str(degree_raw).strip().lower()
            degree_map = {
                "bachelor": "bachelor",
                "cử nhân": "bachelor",
                "cu nhan": "bachelor",
                "engineer": "engineer",
                "kỹ sư": "engineer",
                "ky su": "engineer",
                "master": "master",
                "thạc sĩ": "master",
                "thac si": "master",
            }
            adapter["degree_level"] = degree_map.get(degree, "bachelor")
        else:
            adapter["degree_level"] = "bachelor"


# ============================================================
# Module-level helpers
# ============================================================


def _normalize_admission_method(raw: str) -> str:
    """
    Map chuỗi admission_method thô sang giá trị enum chuẩn.

    Chiến lược:
    1. Nếu đã là enum hợp lệ → trả về ngay
    2. Tìm trong bảng mapping (case-insensitive)
    3. Tìm từ khóa trong chuỗi
    4. Fallback → "THPT"

    Args:
        raw: Phương thức xét tuyển thô từ HTML

    Returns:
        Giá trị enum hợp lệ: "THPT" | "hoc_ba" | "DGNL" | "SAT" |
                             "xet_tuyen_thang" | "khac"
    """
    if not raw or not isinstance(raw, str):
        return "THPT"

    text = raw.strip()

    # Bước 1: Đã là enum hợp lệ
    if text in _VALID_ADMISSION_METHODS:
        return text

    # Bước 2: Tra bảng mapping (case-insensitive)
    text_lower = text.lower().strip()
    if text_lower in _ADMISSION_METHOD_MAP:
        return _ADMISSION_METHOD_MAP[text_lower]

    # Bước 3: Tìm từ khóa trong chuỗi
    text_lower_no_accent = _remove_accents_simple(text_lower)

    keyword_rules = [
        (["hoc_ba", "hoc ba", "hoc-ba", "học bạ", "hocba"], "hoc_ba"),
        (["dgnl", "danh gia nang luc", "đánh giá"], "DGNL"),
        (["sat", "ielts", "toefl", "chứng chỉ", "chung chi"], "SAT"),
        (["thẳng", "thang", "ưu tiên", "uu tien"], "xet_tuyen_thang"),
        (["thpt", "tot nghiep", "tốt nghiệp"], "THPT"),
    ]

    for keywords, method in keyword_rules:
        for kw in keywords:
            if kw in text_lower or kw in text_lower_no_accent:
                return method

    logger.debug(
        "[NormalizationPipeline] Không map được admission_method: %r → THPT", raw
    )
    return "THPT"


def _clean_text_field(text: str, max_length: Optional[int] = None) -> str:
    """
    Làm sạch trường text thông thường:
    - Strip khoảng trắng đầu/cuối
    - Chuẩn hóa khoảng trắng nội dung
    - Xóa ký tự điều khiển
    - Giới hạn độ dài (nếu có)

    Args:
        text:       Chuỗi cần làm sạch
        max_length: Độ dài tối đa (None = không giới hạn)

    Returns:
        Chuỗi đã làm sạch
    """
    import unicodedata

    if not text:
        return ""

    # Chuẩn hóa Unicode NFC
    text = unicodedata.normalize("NFC", text)

    # Xóa ký tự điều khiển
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch == "\n")

    # Chuẩn hóa khoảng trắng (giữ nguyên xuống dòng)
    lines = text.splitlines()
    lines = [re.sub(r" +", " ", line).strip() for line in lines]
    text = "\n".join(line for line in lines if line)

    # Giới hạn độ dài
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip()

    return text.strip()


def _deduplicate_strings(items: list) -> list[str]:
    """
    Làm sạch danh sách string: strip, xóa rỗng, loại trùng.
    Giữ nguyên thứ tự xuất hiện đầu tiên.

    Args:
        items: Danh sách các phần tử (có thể có trùng lặp)

    Returns:
        Danh sách đã loại trùng, giữ thứ tự
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item:
            continue
        s = str(item).strip()
        if s and s not in seen:
            result.append(s)
            seen.add(s)
    return result


def _remove_accents_simple(text: str) -> str:
    """
    Xóa dấu tiếng Việt đơn giản (không cần import utils để tránh circular).

    Args:
        text: Chuỗi tiếng Việt

    Returns:
        Chuỗi không dấu
    """
    import unicodedata

    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
