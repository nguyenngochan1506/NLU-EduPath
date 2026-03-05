# ============================================================
# pipelines/validation_pipeline.py
# Pipeline 1 (priority 100): Validate dữ liệu thô từ spider
#
# Nhiệm vụ:
#   - Kiểm tra các trường bắt buộc không được thiếu/rỗng
#   - Validate kiểu dữ liệu (int, float, str)
#   - Validate giá trị hợp lệ (năm, điểm, URL, ...)
#   - Dùng Pydantic schema tương ứng với từng loại item
#   - Drop item nếu không hợp lệ và ghi log lý do
#
# Items được xử lý:
#   AdmissionScoreItem → AdmissionScoreRaw (Pydantic)
#   UniversityItem     → UniversityCreateSchema (Pydantic)
#   MajorItem          → MajorCreate (Pydantic)
# ============================================================

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from itemadapter import ItemAdapter
from pydantic import ValidationError
from scrapy import Spider
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """
    Pipeline đầu tiên trong chuỗi xử lý (priority=100).

    Validate dữ liệu thô từ spider bằng Pydantic schema.
    Nếu validation thất bại → raise DropItem để loại bỏ item.

    Thống kê:
        - items_validated  : Số item hợp lệ
        - items_dropped    : Số item bị loại
        - drop_reasons     : Dict {lý_do → số_lần}
    """

    def __init__(self) -> None:
        self.items_validated = 0
        self.items_dropped = 0
        self.drop_reasons: dict[str, int] = {}

    # ----------------------------------------------------------
    # Scrapy hooks
    # ----------------------------------------------------------

    def open_spider(self, spider: Spider) -> None:
        logger.info("[ValidationPipeline] Spider '%s' bắt đầu.", spider.name)
        self.items_validated = 0
        self.items_dropped = 0
        self.drop_reasons = {}

    def close_spider(self, spider: Spider) -> None:
        logger.info(
            "[ValidationPipeline] Spider '%s' kết thúc. "
            "Hợp lệ=%d | Loại=%d | Lý do: %s",
            spider.name,
            self.items_validated,
            self.items_dropped,
            self.drop_reasons,
        )

    def process_item(self, item: Any, spider: Spider) -> Any:
        """
        Xác định loại item và gọi validator tương ứng.
        Trả về item nếu hợp lệ, raise DropItem nếu không.
        """
        adapter = ItemAdapter(item)
        item_type = type(item).__name__

        try:
            if item_type == "AdmissionScoreItem":
                self._validate_admission_score(adapter, spider)
            elif item_type == "UniversityItem":
                self._validate_university(adapter, spider)
            elif item_type == "MajorItem":
                self._validate_major(adapter, spider)
            else:
                # Item type không biết → pass qua để pipeline sau xử lý
                logger.warning(
                    "[ValidationPipeline] Item type không biết: %s – bỏ qua validate.",
                    item_type,
                )
                return item

        except DropItem:
            raise
        except Exception as exc:
            reason = f"Lỗi không mong đợi: {exc}"
            self._drop(item_type, reason)

        self.items_validated += 1
        return item

    # ----------------------------------------------------------
    # Validators cho từng loại item
    # ----------------------------------------------------------

    def _validate_admission_score(self, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Validate AdmissionScoreItem bằng AdmissionScoreRaw schema.

        Kiểm tra:
        - university_code : bắt buộc, không rỗng
        - major_name_raw  : bắt buộc, không rỗng
        - year            : bắt buộc, trong khoảng [2018, 2030]
        - cutoff_score    : tùy chọn, nếu có thì trong [10.0, 30.0]
        - scraped_at      : tự động điền nếu thiếu
        - source_url      : tùy chọn, phải là URL hợp lệ nếu có
        """
        from models.admission_score import AdmissionScoreRaw

        # Tự động điền scraped_at nếu thiếu
        if not adapter.get("scraped_at"):
            adapter["scraped_at"] = datetime.now(tz=timezone.utc)

        # Kiểm tra trường bắt buộc
        university_code = adapter.get("university_code")
        if not university_code or not str(university_code).strip():
            self._drop("AdmissionScoreItem", "university_code rỗng hoặc thiếu")

        major_name_raw = adapter.get("major_name_raw")
        if not major_name_raw or not str(major_name_raw).strip():
            self._drop("AdmissionScoreItem", "major_name_raw rỗng hoặc thiếu")

        year = adapter.get("year")
        if year is None:
            self._drop("AdmissionScoreItem", "year thiếu")

        # Validate kiểu dữ liệu và giá trị cho year
        try:
            year_int = int(year)
            if not (2018 <= year_int <= 2030):
                self._drop(
                    "AdmissionScoreItem",
                    f"year={year_int} nằm ngoài khoảng [2018, 2030]",
                )
        except (TypeError, ValueError):
            self._drop("AdmissionScoreItem", f"year không hợp lệ: {year!r}")

        # Validate cutoff_score nếu có
        cutoff_raw = adapter.get("cutoff_score")
        if cutoff_raw is not None:
            try:
                score = float(cutoff_raw)
                if not (0.0 <= score <= 100.0):
                    # Không drop – chỉ xóa giá trị không hợp lệ, ghi warning
                    logger.warning(
                        "[ValidationPipeline] cutoff_score=%s ngoài khoảng [0,100] "
                        "tại %s năm %s – set None.",
                        score,
                        university_code,
                        year,
                    )
                    adapter["cutoff_score"] = None
                else:
                    adapter["cutoff_score"] = round(score, 2)
            except (TypeError, ValueError):
                logger.warning(
                    "[ValidationPipeline] cutoff_score không parse được: %r – set None.",
                    cutoff_raw,
                )
                adapter["cutoff_score"] = None

        # Validate quota nếu có
        quota_raw = adapter.get("quota")
        if quota_raw is not None:
            try:
                quota = int(quota_raw)
                adapter["quota"] = quota if quota > 0 else None
            except (TypeError, ValueError):
                adapter["quota"] = None

        # Validate URL nếu có
        source_url = adapter.get("source_url")
        if source_url and not _is_valid_url(str(source_url)):
            logger.warning(
                "[ValidationPipeline] source_url không hợp lệ: %r – set None.",
                source_url,
            )
            adapter["source_url"] = None

        # Validate bằng Pydantic schema để đảm bảo toàn diện
        try:
            AdmissionScoreRaw(
                university_code=str(adapter["university_code"]).strip(),
                major_name_raw=str(adapter["major_name_raw"]).strip(),
                year=int(adapter["year"]),
                admission_method=str(adapter.get("admission_method") or "THPT"),
                subject_combination=str(adapter.get("subject_combination") or "KHAC"),
                cutoff_score=adapter.get("cutoff_score"),
                quota=adapter.get("quota"),
                note=adapter.get("note"),
                scraped_at=adapter["scraped_at"],
                source_url=adapter.get("source_url"),
            )
        except ValidationError as exc:
            errors = _format_pydantic_errors(exc)
            self._drop("AdmissionScoreItem", f"Pydantic validation lỗi: {errors}")

    def _validate_university(self, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Validate UniversityItem bằng UniversityCreateSchema.
        """
        from models.university import UniversityCreateSchema

        # Tự động điền scraped_at nếu thiếu
        if not adapter.get("scraped_at"):
            adapter["scraped_at"] = datetime.now(tz=timezone.utc)

        # Kiểm tra trường bắt buộc
        university_code = adapter.get("university_code")
        if not university_code or not str(university_code).strip():
            self._drop("UniversityItem", "university_code rỗng hoặc thiếu")

        name = adapter.get("name")
        if not name or not str(name).strip():
            self._drop("UniversityItem", "name rỗng hoặc thiếu")

        # Validate university_type
        university_type = adapter.get("university_type")
        if university_type and university_type not in {
            "public",
            "private",
            "foreign_affiliated",
        }:
            logger.warning(
                "[ValidationPipeline] university_type không hợp lệ: %r – set None.",
                university_type,
            )
            adapter["university_type"] = None

        # Validate region
        region = adapter.get("region")
        if region and region not in {"north", "central", "south"}:
            logger.warning(
                "[ValidationPipeline] region không hợp lệ: %r – set None.", region
            )
            adapter["region"] = None

        # Validate URLs
        for url_field in ("website", "admission_url", "logo_url", "source_url"):
            val = adapter.get(url_field)
            if val and not _is_valid_url(str(val)):
                logger.warning(
                    "[ValidationPipeline] %s không hợp lệ: %r – set None.",
                    url_field,
                    val,
                )
                adapter[url_field] = None

        # Validate established_year
        year = adapter.get("established_year")
        if year is not None:
            try:
                year_int = int(year)
                if not (1800 <= year_int <= 2100):
                    adapter["established_year"] = None
            except (TypeError, ValueError):
                adapter["established_year"] = None

        # Cuối cùng: Pydantic validation
        try:
            UniversityCreateSchema(
                university_code=str(adapter["university_code"]).strip().upper(),
                name=str(adapter["name"]).strip(),
                short_name=adapter.get("short_name"),
                university_type=adapter.get("university_type"),
                region=adapter.get("region"),
                province=adapter.get("province"),
                address=adapter.get("address"),
                website=adapter.get("website"),
                admission_url=adapter.get("admission_url"),
                logo_url=adapter.get("logo_url"),
                tuition_min=adapter.get("tuition_min"),
                tuition_max=adapter.get("tuition_max"),
                established_year=adapter.get("established_year"),
                scraped_at=adapter["scraped_at"],
                source_url=adapter.get("source_url"),
            )
        except ValidationError as exc:
            errors = _format_pydantic_errors(exc)
            self._drop("UniversityItem", f"Pydantic validation lỗi: {errors}")

    def _validate_major(self, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Validate MajorItem bằng MajorCreate schema.
        """
        from models.major import MajorCreate

        # Tự động điền scraped_at nếu thiếu
        if not adapter.get("scraped_at"):
            adapter["scraped_at"] = datetime.now(tz=timezone.utc)

        # Kiểm tra trường bắt buộc
        major_code = adapter.get("major_code")
        if not major_code or not str(major_code).strip():
            self._drop("MajorItem", "major_code rỗng hoặc thiếu")

        name = adapter.get("name")
        if not name or not str(name).strip():
            self._drop("MajorItem", "name rỗng hoặc thiếu")

        # Validate major_code format (7 chữ số)
        import re

        if not re.match(r"^\d{7}$", str(major_code).strip()):
            self._drop(
                "MajorItem",
                f"major_code không đúng định dạng 7 chữ số: {major_code!r}",
            )

        # Đảm bảo list fields là list
        for list_field in (
            "career_options",
            "required_skills",
            "subject_combinations",
            "holland_types",
            "career_anchor_tags",
        ):
            val = adapter.get(list_field)
            if val is None:
                adapter[list_field] = []
            elif not isinstance(val, list):
                adapter[list_field] = [str(val)] if val else []

        # Validate degree_level
        degree_level = adapter.get("degree_level")
        if degree_level and degree_level not in {"bachelor", "engineer", "master"}:
            adapter["degree_level"] = "bachelor"

        # Pydantic validation
        try:
            MajorCreate(
                major_code=str(adapter["major_code"]).strip(),
                name=str(adapter["name"]).strip(),
                major_group=adapter.get("major_group"),
                major_group_code=adapter.get("major_group_code"),
                description=adapter.get("description"),
                career_options=adapter.get("career_options", []),
                required_skills=adapter.get("required_skills", []),
                subject_combinations=adapter.get("subject_combinations", []),
                holland_types=adapter.get("holland_types", []),
                career_anchor_tags=adapter.get("career_anchor_tags", []),
                study_duration=adapter.get("study_duration"),
                degree_level=adapter.get("degree_level"),
                scraped_at=adapter["scraped_at"],
                source_url=adapter.get("source_url"),
            )
        except ValidationError as exc:
            errors = _format_pydantic_errors(exc)
            self._drop("MajorItem", f"Pydantic validation lỗi: {errors}")

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _drop(self, item_type: str, reason: str) -> None:
        """
        Tăng counter, ghi log, và raise DropItem.
        """
        self.items_dropped += 1
        self.drop_reasons[reason] = self.drop_reasons.get(reason, 0) + 1
        msg = f"[ValidationPipeline] Drop {item_type}: {reason}"
        logger.warning(msg)
        raise DropItem(msg)


# ============================================================
# Module-level helpers
# ============================================================


def _is_valid_url(url: str) -> bool:
    """Kiểm tra URL có hợp lệ không (bắt đầu bằng http/https)."""
    if not url:
        return False
    url = url.strip()
    return url.startswith("http://") or url.startswith("https://")


def _format_pydantic_errors(exc: ValidationError) -> str:
    """
    Format lỗi Pydantic thành chuỗi ngắn gọn để log.

    VD: "year: Value should be >= 2018 | cutoff_score: Value must be <= 30"
    """
    parts = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        parts.append(f"{field}: {msg}")
    return " | ".join(parts)
