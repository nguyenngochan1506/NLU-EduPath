# ============================================================
# pipelines/storage_pipeline.py
# Pipeline 4 (priority 400): Lưu dữ liệu vào PostgreSQL
#
# Nhiệm vụ:
#   - Resolve university_id và major_id từ DB (dùng code/tên)
#   - Upsert AdmissionScoreItem → bảng admission_scores
#   - Upsert UniversityItem     → bảng universities
#   - Upsert MajorItem          → bảng majors
#   - Ghi crawl_log khi spider bắt đầu/kết thúc
#   - Flush theo batch để giảm tải DB
#
# Items được xử lý:
#   AdmissionScoreItem, UniversityItem, MajorItem
#
# Lưu ý quan trọng:
#   - Pipeline này KHÔNG quản lý transaction per-item.
#     Toàn bộ batch được commit theo BATCH_SIZE hoặc khi spider đóng.
#   - Nếu item thiếu university_id/major_id sau khi resolve → log warning + skip.
#   - StoragePipeline là pipeline CUỐI CÙNG → item đến đây đã qua validate,
#     normalize, dedup.
# ============================================================

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from itemadapter import ItemAdapter
from scrapy import Spider
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

# Số item tích lũy trước khi flush (commit) vào DB
_BATCH_SIZE = 50


class StoragePipeline:
    """
    Pipeline cuối cùng trong chuỗi xử lý (priority=400).

    Nhận item đã được validate, normalize, dedup và lưu vào PostgreSQL
    qua các Repository. Mọi thao tác được thực hiện trong một session
    duy nhất trên suốt vòng đời của spider.

    Thống kê:
        records_new     : Số bản ghi mới được INSERT
        records_updated : Số bản ghi cũ được UPDATE
        records_failed  : Số bản ghi lỗi khi lưu
        _pending        : Số item đang chờ flush
    """

    def __init__(self) -> None:
        self.records_new = 0
        self.records_updated = 0
        self.records_failed = 0
        self.records_skipped = 0  # Tách riêng phần bỏ qua do không khớp mapping
        self._pending = 0

        # DB session và factory (khởi tạo trong open_spider)
        self._session: Any = None

        # UUID của CrawlLog entry cho run này
        self._crawl_log_id: Optional[uuid.UUID] = None

        # Cache resolve: university_code → UUID, major_code → UUID
        # Để tránh query DB lặp lại cho cùng một trường/ngành trong một run
        self._university_id_cache: dict[str, Optional[uuid.UUID]] = {}
        self._major_id_cache: dict[str, Optional[uuid.UUID]] = {}

    # ----------------------------------------------------------
    # Scrapy hooks
    # ----------------------------------------------------------

    def open_spider(self, spider: Spider) -> None:
        """
        Khởi tạo DB session và tạo CrawlLog entry khi spider bắt đầu.
        """
        logger.info("[StoragePipeline] Spider '%s' bắt đầu.", spider.name)

        # Reset stats
        self.records_new = 0
        self.records_updated = 0
        self.records_failed = 0
        self.records_skipped = 0
        self._pending = 0
        self._university_id_cache.clear()
        self._major_id_cache.clear()

        # Khởi tạo DB session
        try:
            from db.connection import get_session_factory

            factory = get_session_factory()
            self._session = factory()
            logger.info("[StoragePipeline] DB session khởi tạo thành công.")
        except Exception as exc:
            logger.error(
                "[StoragePipeline] Không thể khởi tạo DB session: %s. "
                "StoragePipeline sẽ không lưu dữ liệu.",
                exc,
            )
            self._session = None
            return

        # Tạo CrawlLog entry
        self._crawl_log_id = self._create_crawl_log(spider.name)

    def close_spider(self, spider: Spider) -> None:
        """
        Flush dữ liệu còn lại, cập nhật CrawlLog, và đóng session.
        """
        if self._session is None:
            return

        try:
            # Flush batch còn lại
            if self._pending > 0:
                self._commit_session(spider)

            # Cập nhật CrawlLog với kết quả cuối
            self._update_crawl_log(
                status="success" if self.records_failed == 0 else "partial",
                finished_at=datetime.now(tz=timezone.utc),
            )

            logger.info(
                "[StoragePipeline] Spider '%s' kết thúc. Mới=%d | Cập nhật=%d | Bỏ qua=%d | Lỗi=%d",
                spider.name,
                self.records_new,
                self.records_updated,
                self.records_skipped,
                self.records_failed,
            )

        except Exception as exc:
            logger.error("[StoragePipeline] Lỗi khi close_spider: %s", exc)
            self._update_crawl_log(status="failed", error_summary=str(exc))
        finally:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def process_item(self, item: Any, spider: Spider) -> Any:
        """
        Lưu item vào DB theo loại.

        Trả về item sau khi lưu (để pipeline tiếp theo nhận nếu có).
        Raise DropItem nếu không lưu được do thiếu dữ liệu quan trọng.
        """
        if self._session is None:
            logger.warning(
                "[StoragePipeline] Không có DB session – bỏ qua item %s.",
                type(item).__name__,
            )
            return item

        adapter = ItemAdapter(item)
        item_type = type(item).__name__

        try:
            if item_type == "AdmissionScoreItem":
                self._store_admission_score(item, adapter, spider)
            elif item_type == "UniversityItem":
                self._store_university(item, adapter, spider)
            elif item_type == "MajorItem":
                self._store_major(item, adapter, spider)
            else:
                logger.debug(
                    "[StoragePipeline] Item type không biết: %s – bỏ qua.", item_type
                )
                return item

            # Flush theo batch
            self._pending += 1
            if self._pending >= _BATCH_SIZE:
                self._commit_session(spider)

        except DropItem:
            raise
        except Exception as exc:
            self.records_failed += 1
            logger.error(
                "[StoragePipeline] Lỗi khi lưu %s: %s", item_type, exc, exc_info=True
            )
            # Rollback session để tiếp tục với item tiếp theo
            try:
                self._session.rollback()
            except Exception:
                pass

        return item

    # ----------------------------------------------------------
    # Store theo loại item
    # ----------------------------------------------------------

    def _store_admission_score(
        self, item: Any, adapter: ItemAdapter, spider: Spider
    ) -> None:
        """
        Lưu AdmissionScoreItem vào bảng admission_scores.

        Quy trình:
        1. Resolve university_id từ university_code
        2. Resolve major_id từ major_code (hoặc major_name_raw làm fallback)
        3. Build AdmissionScoreCreate schema
        4. Upsert qua ScoreRepository
        """
        from models.admission_score import AdmissionScoreCreate

        university_code = str(adapter.get("university_code", "")).strip().upper()
        major_code = str(adapter.get("major_code", "") or "").strip()
        major_name_raw = str(adapter.get("major_name_raw", "") or "").strip()
        year = int(adapter.get("year", 0))
        admission_method = str(adapter.get("admission_method") or "THPT")
        subject_combination = str(adapter.get("subject_combination") or "KHAC")
        cutoff_score = adapter.get("cutoff_score")
        quota = adapter.get("quota")
        note = adapter.get("note")
        scraped_at = adapter.get("scraped_at") or datetime.now(tz=timezone.utc)
        source_url = adapter.get("source_url")

        # 1. Resolve university_id (Tự động tạo nếu thiếu)
        university_id = adapter.get("_university_id") or self._resolve_university_id(university_code)
        
        if university_id is None:
            university_id = self._create_university_on_the_fly(university_code, spider)
            if university_id:
                logger.info("🆕 [NEW SCHOOL] Tự động tạo trường: %s", university_code)
                self._university_id_cache[university_code] = university_id
            else:
                self.records_failed += 1
                raise DropItem(f"Lỗi tạo trường: {university_code}")

        # 2. Resolve major_id (Tự động tạo nếu thiếu)
        major_id = adapter.get("_major_id") or self._resolve_major_id(
            major_code=major_code, major_name_raw=major_name_raw
        )
        
        if major_id is None:
            major_id = self._create_major_on_the_fly(major_code, major_name_raw)
            if major_id:
                logger.info("🎯 [NEW MAJOR] Tự động tạo ngành: %s", major_name_raw)
                if major_code: self._major_id_cache[major_code] = major_id
                self._major_id_cache[f"name:{major_name_raw.lower()}"] = major_id
            else:
                self.records_failed += 1
                raise DropItem(f"Lỗi tạo ngành: {major_name_raw}")

        # 3. Build schema
        schema = AdmissionScoreCreate(
            university_id=university_id,
            major_id=major_id,
            year=year,
            admission_method=admission_method,
            subject_combination=subject_combination,
            cutoff_score=float(cutoff_score) if cutoff_score is not None else None,
            quota=int(quota) if quota is not None else None,
            note=str(note)[:500] if note else None,
            scraped_at=_ensure_utc(scraped_at),
            source_url=str(source_url)[:500] if source_url else None,
        )

        # 4. Upsert
        from db.repositories.score_repo import ScoreRepository

        repo = ScoreRepository(self._session)
        _, created = repo.upsert(schema)

        if created:
            self.records_new += 1
            logger.debug(
                "[StoragePipeline] INSERT score: %s / %s / %s / %s / %s",
                university_code,
                major_code or major_name_raw,
                year,
                admission_method,
                subject_combination,
            )
        else:
            self.records_updated += 1
            logger.debug(
                "[StoragePipeline] UPDATE score: %s / %s / %s",
                university_code,
                major_code or major_name_raw,
                year,
            )

    def _store_university(
        self, item: Any, adapter: ItemAdapter, spider: Spider
    ) -> None:
        """
        Lưu UniversityItem vào bảng universities.

        Dùng upsert để tránh duplicate khi chạy lại.
        """
        from models.university import UniversityCreateSchema

        university_code = str(adapter.get("university_code", "")).strip().upper()
        name = str(adapter.get("name", "")).strip()
        scraped_at = adapter.get("scraped_at") or datetime.now(tz=timezone.utc)

        if not university_code or not name:
            logger.warning(
                "[StoragePipeline] UniversityItem thiếu university_code hoặc name – bỏ qua."
            )
            self.records_failed += 1
            return

        schema = UniversityCreateSchema(
            university_code=university_code,
            name=name,
            short_name=_opt_str(adapter.get("short_name"), 50),
            university_type=adapter.get("university_type"),
            region=adapter.get("region"),
            province=_opt_str(adapter.get("province"), 100),
            address=_opt_str(adapter.get("address"), 500),
            website=_opt_str(adapter.get("website"), 500),
            admission_url=_opt_str(adapter.get("admission_url"), 500),
            logo_url=_opt_str(adapter.get("logo_url"), 500),
            tuition_min=_opt_int(adapter.get("tuition_min")),
            tuition_max=_opt_int(adapter.get("tuition_max")),
            established_year=_opt_int(adapter.get("established_year")),
            scraped_at=_ensure_utc(scraped_at),
            source_url=_opt_str(adapter.get("source_url"), 500),
        )

        from db.repositories.university_repo import UniversityRepository

        repo = UniversityRepository(self._session)
        _, created = repo.upsert(schema)

        if created:
            self.records_new += 1
            # Xóa cache cũ để force re-resolve
            self._university_id_cache.pop(university_code, None)
            logger.debug(
                "[StoragePipeline] INSERT university: %s – %s", university_code, name
            )
        else:
            self.records_updated += 1
            logger.debug(
                "[StoragePipeline] UPDATE university: %s – %s", university_code, name
            )

    def _store_major(self, item: Any, adapter: ItemAdapter, spider: Spider) -> None:
        """
        Lưu MajorItem vào bảng majors.

        Dùng upsert theo major_code.
        """
        from models.major import MajorCreate

        major_code = str(adapter.get("major_code", "")).strip()
        name = str(adapter.get("name", "")).strip()
        scraped_at = adapter.get("scraped_at") or datetime.now(tz=timezone.utc)

        if not major_code or not name:
            logger.warning(
                "[StoragePipeline] MajorItem thiếu major_code hoặc name – bỏ qua."
            )
            self.records_failed += 1
            return

        schema = MajorCreate(
            major_code=major_code,
            name=name,
            major_group=_opt_str(adapter.get("major_group"), 100),
            major_group_code=_opt_str(adapter.get("major_group_code"), 10),
            description=adapter.get("description"),
            career_options=adapter.get("career_options") or [],
            required_skills=adapter.get("required_skills") or [],
            subject_combinations=adapter.get("subject_combinations") or [],
            holland_types=adapter.get("holland_types") or [],
            career_anchor_tags=adapter.get("career_anchor_tags") or [],
            study_duration=_opt_int(adapter.get("study_duration")),
            degree_level=_opt_str(adapter.get("degree_level"), 20),
            scraped_at=_ensure_utc(scraped_at),
            source_url=_opt_str(adapter.get("source_url"), 500),
        )

        from db.repositories.major_repo import MajorRepository

        repo = MajorRepository(self._session)
        _, created = repo.upsert(schema)

        if created:
            self.records_new += 1
            # Xóa cache cũ để force re-resolve
            self._major_id_cache.pop(major_code, None)
            logger.debug("[StoragePipeline] INSERT major: %s – %s", major_code, name)
        else:
            self.records_updated += 1
            logger.debug("[StoragePipeline] UPDATE major: %s – %s", major_code, name)

    # ----------------------------------------------------------
    # On-the-fly Creation Helpers
    # ----------------------------------------------------------

    def _create_university_on_the_fly(self, code: str, spider: Spider) -> Optional[uuid.UUID]:
        """Tự động tạo bản ghi trường đại học mới."""
        from models.university import UniversityCreateSchema
        from db.repositories.university_repo import UniversityRepository
        
        # Tạo schema cơ bản nhất
        schema = UniversityCreateSchema(
            university_code=code,
            name=f"Trường {code} (Tự động khám phá)",
            university_type="public",
            region="south", # Mặc định
            scraped_at=datetime.now(tz=timezone.utc)
        )
        
        try:
            repo = UniversityRepository(self._session)
            uni, _ = repo.upsert(schema)
            self._session.flush()
            return uni.id
        except Exception as exc:
            logger.error("[StoragePipeline] Lỗi tạo trường on-the-fly: %s", exc)
            return None

    def _create_major_on_the_fly(self, code: Optional[str], name: str) -> Optional[uuid.UUID]:
        """Tự động tạo bản ghi ngành học mới."""
        from models.major import MajorCreate
        from db.repositories.major_repo import MajorRepository
        
        # Nếu không có mã, tạo mã giả hoặc để None nếu schema cho phép
        major_code = code or f"AUTO-{uuid.uuid4().hex[:6].upper()}"
        
        schema = MajorCreate(
            major_code=major_code,
            name=name,
            major_group="Chưa phân loại",
            major_group_code="000",
            study_duration=4,
            degree_level="bachelor",
            scraped_at=datetime.now(tz=timezone.utc)
        )
        
        try:
            repo = MajorRepository(self._session)
            # Dùng repo.create thay vì upsert để đảm bảo ID mới
            # Hoặc dùng upsert nếu muốn reuse theo name
            major, _ = repo.upsert(schema)
            self._session.flush()
            return major.id
        except Exception as exc:
            logger.error("[StoragePipeline] Lỗi tạo ngành on-the-fly: %s", exc)
            return None

    # ----------------------------------------------------------
    # Resolve helpers (với cache)
    # ----------------------------------------------------------

    def _resolve_university_id(self, university_code: str) -> Optional[uuid.UUID]:
        """
        Resolve university_code → UUID.

        Kết quả được cache trong session để tránh query lặp lại.

        Args:
            university_code: Mã trường (VD: "QSB", "BKA")

        Returns:
            UUID của trường, hoặc None nếu không tìm thấy.
        """
        if not university_code:
            return None

        # Check cache trước
        if university_code in self._university_id_cache:
            return self._university_id_cache[university_code]

        # Query DB
        try:
            from db.repositories.university_repo import UniversityRepository

            repo = UniversityRepository(self._session)
            university = repo.get_by_code(university_code)

            if university:
                self._university_id_cache[university_code] = university.id
                return university.id
            else:
                self._university_id_cache[university_code] = None
                return None

        except Exception as exc:
            logger.error(
                "[StoragePipeline] Lỗi khi resolve university_id cho code=%r: %s",
                university_code,
                exc,
            )
            return None

    def _resolve_major_id(
        self,
        *,
        major_code: Optional[str] = None,
        major_name_raw: Optional[str] = None,
    ) -> Optional[uuid.UUID]:
        """
        Resolve major_code hoặc major_name_raw → UUID.

        Chiến lược:
        1. Nếu có major_code → tra cache, nếu miss → query DB theo code
        2. Nếu không có code → query DB theo tên (exact match, rồi fuzzy)

        Args:
            major_code:     Mã ngành 7 chữ số (VD: "7480201")
            major_name_raw: Tên ngành đã chuẩn hóa (fallback)

        Returns:
            UUID của ngành, hoặc None nếu không tìm thấy.
        """
        # Bước 1: Resolve theo mã
        if major_code:
            if major_code in self._major_id_cache:
                return self._major_id_cache[major_code]

            try:
                from db.repositories.major_repo import MajorRepository

                repo = MajorRepository(self._session)
                major_id = repo.resolve_major_id(major_code=major_code)

                self._major_id_cache[major_code] = major_id
                return major_id
            except Exception as exc:
                logger.error(
                    "[StoragePipeline] Lỗi khi resolve major_id theo code=%r: %s",
                    major_code,
                    exc,
                )

        # Bước 2: Fallback – resolve theo tên
        if major_name_raw:
            cache_key = f"name:{major_name_raw.lower()}"
            if cache_key in self._major_id_cache:
                return self._major_id_cache[cache_key]

            try:
                from db.repositories.major_repo import MajorRepository

                repo = MajorRepository(self._session)
                major_id = repo.resolve_major_id(major_name_raw=major_name_raw)

                self._major_id_cache[cache_key] = major_id
                return major_id
            except Exception as exc:
                logger.error(
                    "[StoragePipeline] Lỗi khi resolve major_id theo name=%r: %s",
                    major_name_raw,
                    exc,
                )

        return None

    # ----------------------------------------------------------
    # Session & CrawlLog management
    # ----------------------------------------------------------

    def _commit_session(self, spider: Spider) -> None:
        """
        Commit session hiện tại và reset pending counter.
        """
        try:
            self._session.commit()
            logger.debug(
                "[StoragePipeline] Commit %d items (new=%d, updated=%d).",
                self._pending,
                self.records_new,
                self.records_updated,
            )
            self._pending = 0
        except Exception as exc:
            logger.error("[StoragePipeline] Lỗi khi commit: %s", exc, exc_info=True)
            try:
                self._session.rollback()
            except Exception:
                pass
            raise

    def _create_crawl_log(self, spider_name: str) -> Optional[uuid.UUID]:
        """
        Tạo một bản ghi CrawlLog mới khi spider bắt đầu.

        Returns:
            UUID của CrawlLog, hoặc None nếu tạo thất bại.
        """
        if self._session is None:
            return None

        try:
            from models.crawl_log import CrawlLog

            log_id = uuid.uuid4()
            log = CrawlLog(
                id=log_id,
                spider_name=spider_name,
                status="running",
                started_at=datetime.now(tz=timezone.utc),
                records_new=0,
                records_updated=0,
                records_failed=0,
            )
            self._session.add(log)
            self._session.commit()
            logger.info(
                "[StoragePipeline] CrawlLog tạo thành công: id=%s spider=%s",
                log_id,
                spider_name,
            )
            return log_id
        except Exception as exc:
            logger.warning("[StoragePipeline] Không thể tạo CrawlLog: %s", exc)
            try:
                self._session.rollback()
            except Exception:
                pass
            return None

    def _update_crawl_log(
        self,
        status: str,
        finished_at: Optional[datetime] = None,
        error_summary: Optional[str] = None,
    ) -> None:
        """
        Cập nhật CrawlLog với kết quả khi spider kết thúc.

        Args:
            status:       "success" | "partial" | "failed"
            finished_at:  Thời điểm kết thúc (mặc định: bây giờ)
            error_summary: Mô tả lỗi (nếu có)
        """
        if self._session is None or self._crawl_log_id is None:
            return

        try:
            from models.crawl_log import CrawlLog

            log = self._session.get(CrawlLog, self._crawl_log_id)
            if log is None:
                return

            log.status = status
            log.finished_at = finished_at or datetime.now(tz=timezone.utc)
            log.records_new = self.records_new
            log.records_updated = self.records_updated
            log.records_failed = self.records_failed
            if error_summary:
                log.error_summary = error_summary[:2000]  # Giới hạn độ dài

            self._session.commit()
            logger.info(
                "[StoragePipeline] CrawlLog cập nhật: status=%s new=%d updated=%d failed=%d",
                status,
                self.records_new,
                self.records_updated,
                self.records_failed,
            )
        except Exception as exc:
            logger.error("[StoragePipeline] Không thể cập nhật CrawlLog: %s", exc)
            try:
                self._session.rollback()
            except Exception:
                pass


# ============================================================
# Module-level helpers
# ============================================================


def _ensure_utc(dt: Any) -> datetime:
    """
    Đảm bảo datetime có timezone UTC.

    Nếu dt đã có timezone → convert sang UTC.
    Nếu dt là naive → gán UTC.
    Nếu dt là string ISO → parse rồi gán UTC.

    Args:
        dt: Giá trị datetime (datetime object, string ISO, hoặc None)

    Returns:
        datetime với timezone UTC
    """
    if dt is None:
        return datetime.now(tz=timezone.utc)

    if isinstance(dt, str):
        try:
            from datetime import datetime as dt_cls

            parsed = dt_cls.fromisoformat(dt.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return datetime.now(tz=timezone.utc)

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    return datetime.now(tz=timezone.utc)


def _opt_str(value: Any, max_length: Optional[int] = None) -> Optional[str]:
    """
    Chuyển value thành Optional[str], strip khoảng trắng.
    Trả về None nếu value rỗng hoặc None.

    Args:
        value:      Giá trị đầu vào
        max_length: Độ dài tối đa (None = không giới hạn)

    Returns:
        Chuỗi đã clean, hoặc None.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if max_length and len(s) > max_length:
        s = s[:max_length]
    return s


def _opt_int(value: Any) -> Optional[int]:
    """
    Chuyển value thành Optional[int].
    Trả về None nếu không parse được hoặc <= 0.

    Args:
        value: Giá trị đầu vào (string, int, float, hoặc None)

    Returns:
        int dương, hoặc None.
    """
    if value is None:
        return None
    try:
        result = int(float(str(value)))
        return result if result > 0 else None
    except (TypeError, ValueError):
        return None
