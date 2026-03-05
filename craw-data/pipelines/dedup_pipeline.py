# ============================================================
# pipelines/dedup_pipeline.py
# Pipeline 3 (priority 300): Loại bỏ bản ghi trùng lặp
#
# Nhiệm vụ:
#   - Kiểm tra trùng lặp theo composite key TRONG phiên crawl (in-memory set)
#   - Kiểm tra trùng lặp với dữ liệu ĐÃ CÓ trong PostgreSQL (DB lookup)
#   - Đối với AdmissionScoreItem:
#       composite key = (university_code, major_code, year, admission_method, subject_combination)
#   - Đối với UniversityItem:
#       composite key = university_code
#   - Đối với MajorItem:
#       composite key = major_code
#
# Chiến lược:
#   1. Tầng 1 – In-memory set: Nhanh, tránh query DB với item trùng trong cùng 1 run.
#   2. Tầng 2 – Redis (tùy chọn): Tránh trùng lặp giữa các run gần nhau (TTL 24h).
#   3. Tầng 3 – DB query: Kiểm tra cuối cùng trước khi StoragePipeline insert.
#
# Items được xử lý:
#   AdmissionScoreItem, UniversityItem, MajorItem
# ============================================================

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from itemadapter import ItemAdapter
from scrapy import Spider
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class DeduplicationPipeline:
    """
    Pipeline thứ ba trong chuỗi xử lý (priority=300).

    Loại bỏ các item trùng lặp bằng 2 tầng kiểm tra:
    - Tầng 1: In-memory set (fast, per-crawl session)
    - Tầng 2: DB lookup (chính xác, cross-session)

    Item bị coi là trùng nếu composite key của nó đã tồn tại
    ở một trong hai tầng trên.

    Thống kê:
        items_passed   : Số item qua được dedup check
        items_dropped  : Số item bị loại do trùng lặp
        in_memory_hits : Số lần bắt được trùng lặp ở tầng in-memory
        db_hits        : Số lần bắt được trùng lặp ở tầng DB
    """

    def __init__(self) -> None:
        # Tầng 1: in-memory seen set (hash → True)
        self._seen: set[str] = set()

        # Thống kê
        self.items_passed = 0
        self.items_dropped = 0
        self.in_memory_hits = 0
        self.db_hits = 0

        # DB session (khởi tạo lazy trong open_spider)
        self._session: Any = None

        # Redis client (tùy chọn – có thể None nếu Redis không khả dụng)
        self._redis: Any = None

    # ----------------------------------------------------------
    # Scrapy hooks
    # ----------------------------------------------------------

    def open_spider(self, spider: Spider) -> None:
        """Khởi tạo DB session và Redis connection khi spider bắt đầu."""
        logger.info("[DeduplicationPipeline] Spider '%s' bắt đầu.", spider.name)
        self._seen.clear()
        self.items_passed = 0
        self.items_dropped = 0
        self.in_memory_hits = 0
        self.db_hits = 0

        # Khởi tạo DB session
        try:
            from db.connection import get_session_factory

            factory = get_session_factory()
            self._session = factory()
            logger.info("[DeduplicationPipeline] DB session khởi tạo thành công.")
        except Exception as exc:
            logger.error(
                "[DeduplicationPipeline] Không thể khởi tạo DB session: %s – "
                "sẽ chỉ dùng in-memory dedup.",
                exc,
            )
            self._session = None

        # Khởi tạo Redis (tùy chọn)
        self._redis = _try_connect_redis(spider)

    def close_spider(self, spider: Spider) -> None:
        """Đóng DB session và log thống kê."""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass

        logger.info(
            "[DeduplicationPipeline] Spider '%s' kết thúc. "
            "Qua=%d | Loại=%d | InMemoryHits=%d | DBHits=%d",
            spider.name,
            self.items_passed,
            self.items_dropped,
            self.in_memory_hits,
            self.db_hits,
        )

    def process_item(self, item: Any, spider: Spider) -> Any:
        """
        Kiểm tra trùng lặp cho item.

        Trả về item nếu là bản ghi mới, raise DropItem nếu trùng.
        """
        adapter = ItemAdapter(item)
        item_type = type(item).__name__

        if item_type == "AdmissionScoreItem":
            return self._dedup_admission_score(item, adapter, spider)
        elif item_type == "UniversityItem":
            return self._dedup_university(item, adapter, spider)
        elif item_type == "MajorItem":
            return self._dedup_major(item, adapter, spider)
        else:
            # Item type không xử lý – pass through
            return item

    # ----------------------------------------------------------
    # Dedup logic cho từng loại item
    # ----------------------------------------------------------

    def _dedup_admission_score(
        self, item: Any, adapter: ItemAdapter, spider: Spider
    ) -> Any:
        """
        Dedup AdmissionScoreItem theo composite key:
        (university_code, major_code, year, admission_method, subject_combination)

        Lưu ý: major_code được điền bởi NormalizationPipeline (priority=200)
        trước khi đến đây. Nếu chưa có → dùng major_name_raw làm fallback key.
        """
        university_code = str(adapter.get("university_code", "")).strip().upper()
        major_code = str(adapter.get("major_code", "") or "").strip()
        major_name_raw = str(adapter.get("major_name_raw", "") or "").strip()
        year = str(adapter.get("year", "")).strip()
        admission_method = str(adapter.get("admission_method", "THPT")).strip()
        subject_combination = (
            str(adapter.get("subject_combination", "KHAC")).strip().upper()
        )

        # Dùng major_code nếu có, không thì dùng major_name_raw
        major_key = major_code if major_code else major_name_raw.lower()

        composite_key = {
            "university_code": university_code,
            "major_key": major_key,
            "year": year,
            "admission_method": admission_method,
            "subject_combination": subject_combination,
        }
        fingerprint = _make_fingerprint(composite_key)

        # Tầng 1: In-memory check
        if fingerprint in self._seen:
            self.in_memory_hits += 1
            return self._drop(
                "AdmissionScoreItem",
                f"Trùng lặp in-memory: {university_code}/{major_key}/{year}/"
                f"{admission_method}/{subject_combination}",
            )

        # Tầng 2: Redis check (nếu có)
        if self._redis and _redis_exists(self._redis, fingerprint):
            self.in_memory_hits += 1  # Redis cũng coi là fast-cache
            self._seen.add(fingerprint)  # Sync vào in-memory
            return self._drop(
                "AdmissionScoreItem",
                f"Trùng lặp Redis: {university_code}/{major_key}/{year}/"
                f"{admission_method}/{subject_combination}",
            )

        # Tầng 3: DB check (nếu session khả dụng và có major_id)
        major_id = adapter.get("_major_id")  # UUID được set bởi NormalizationPipeline
        university_id = adapter.get(
            "_university_id"
        )  # UUID được set bởi NormalizationPipeline

        if self._session and major_id and university_id:
            try:
                exists = _check_score_exists_in_db(
                    session=self._session,
                    university_id=university_id,
                    major_id=major_id,
                    year=int(year) if year.isdigit() else 0,
                    admission_method=admission_method,
                    subject_combination=subject_combination,
                )
                if exists:
                    self.db_hits += 1
                    self._seen.add(fingerprint)
                    _redis_set(self._redis, fingerprint)
                    return self._drop(
                        "AdmissionScoreItem",
                        f"Đã tồn tại trong DB: {university_code}/{major_key}/{year}/"
                        f"{admission_method}/{subject_combination}",
                    )
            except Exception as exc:
                logger.warning(
                    "[DeduplicationPipeline] Lỗi khi check DB score: %s – bỏ qua check.",
                    exc,
                )

        # Bản ghi mới – đánh dấu fingerprint
        self._seen.add(fingerprint)
        _redis_set(self._redis, fingerprint)
        self.items_passed += 1
        return item

    def _dedup_university(self, item: Any, adapter: ItemAdapter, spider: Spider) -> Any:
        """
        Dedup UniversityItem theo university_code.
        """
        university_code = str(adapter.get("university_code", "")).strip().upper()
        if not university_code:
            self.items_passed += 1
            return item

        fingerprint = _make_fingerprint({"type": "university", "code": university_code})

        # Tầng 1: In-memory
        if fingerprint in self._seen:
            self.in_memory_hits += 1
            return self._drop(
                "UniversityItem",
                f"Trùng lặp in-memory: university_code={university_code}",
            )

        # Tầng 2: Redis
        if self._redis and _redis_exists(self._redis, fingerprint):
            self.in_memory_hits += 1
            self._seen.add(fingerprint)
            return self._drop(
                "UniversityItem",
                f"Trùng lặp Redis: university_code={university_code}",
            )

        # Tầng 3: DB
        if self._session:
            try:
                from db.repositories.university_repo import UniversityRepository

                repo = UniversityRepository(self._session)
                if repo.exists(university_code):
                    self.db_hits += 1
                    self._seen.add(fingerprint)
                    _redis_set(self._redis, fingerprint)
                    return self._drop(
                        "UniversityItem",
                        f"Đã tồn tại trong DB: university_code={university_code}",
                    )
            except Exception as exc:
                logger.warning(
                    "[DeduplicationPipeline] Lỗi khi check DB university: %s – "
                    "bỏ qua check.",
                    exc,
                )

        self._seen.add(fingerprint)
        _redis_set(self._redis, fingerprint)
        self.items_passed += 1
        return item

    def _dedup_major(self, item: Any, adapter: ItemAdapter, spider: Spider) -> Any:
        """
        Dedup MajorItem theo major_code.
        """
        major_code = str(adapter.get("major_code", "")).strip()
        if not major_code:
            self.items_passed += 1
            return item

        fingerprint = _make_fingerprint({"type": "major", "code": major_code})

        # Tầng 1: In-memory
        if fingerprint in self._seen:
            self.in_memory_hits += 1
            return self._drop(
                "MajorItem",
                f"Trùng lặp in-memory: major_code={major_code}",
            )

        # Tầng 2: Redis
        if self._redis and _redis_exists(self._redis, fingerprint):
            self.in_memory_hits += 1
            self._seen.add(fingerprint)
            return self._drop(
                "MajorItem",
                f"Trùng lặp Redis: major_code={major_code}",
            )

        # Tầng 3: DB
        if self._session:
            try:
                from db.repositories.major_repo import MajorRepository

                repo = MajorRepository(self._session)
                if repo.exists(major_code):
                    self.db_hits += 1
                    self._seen.add(fingerprint)
                    _redis_set(self._redis, fingerprint)
                    return self._drop(
                        "MajorItem",
                        f"Đã tồn tại trong DB: major_code={major_code}",
                    )
            except Exception as exc:
                logger.warning(
                    "[DeduplicationPipeline] Lỗi khi check DB major: %s – bỏ qua check.",
                    exc,
                )

        self._seen.add(fingerprint)
        _redis_set(self._redis, fingerprint)
        self.items_passed += 1
        return item

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------

    def _drop(self, item_type: str, reason: str) -> None:
        """Tăng counter và raise DropItem."""
        self.items_dropped += 1
        msg = f"[DeduplicationPipeline] Drop {item_type}: {reason}"
        logger.debug(msg)
        raise DropItem(msg)


# ============================================================
# Module-level helpers
# ============================================================


def _make_fingerprint(data: dict) -> str:
    """
    Tạo fingerprint SHA-256 từ một dict composite key.

    Sắp xếp key để đảm bảo kết quả nhất quán bất kể thứ tự.

    Args:
        data: Dict chứa các thành phần của composite key

    Returns:
        Chuỗi hex 64 ký tự (SHA-256)

    Examples:
        >>> _make_fingerprint({"a": "1", "b": "2"})
        # Chuỗi SHA-256 hex
    """
    # Sắp xếp key để đảm bảo idempotent
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _try_connect_redis(spider: Spider) -> Optional[Any]:
    """
    Thử kết nối Redis. Trả về Redis client nếu thành công, None nếu lỗi.

    Redis được dùng như tầng cache optional – nếu không có thì vẫn hoạt động.
    """
    try:
        import redis
        from config.settings import REDIS_URL

        client = redis.from_url(
            REDIS_URL, socket_connect_timeout=2, decode_responses=True
        )
        client.ping()
        logger.info("[DeduplicationPipeline] Kết nối Redis thành công: %s", REDIS_URL)
        return client
    except Exception as exc:
        logger.warning(
            "[DeduplicationPipeline] Không thể kết nối Redis: %s – "
            "sẽ chỉ dùng in-memory dedup.",
            exc,
        )
        return None


def _redis_exists(client: Any, fingerprint: str) -> bool:
    """
    Kiểm tra fingerprint có tồn tại trong Redis không.

    Args:
        client: Redis client
        fingerprint: SHA-256 fingerprint string

    Returns:
        True nếu đã tồn tại, False nếu chưa hoặc lỗi.
    """
    try:
        return bool(client.exists(f"dedup:{fingerprint}"))
    except Exception as exc:
        logger.debug("[DeduplicationPipeline] Redis EXISTS lỗi: %s", exc)
        return False


def _redis_set(
    client: Optional[Any], fingerprint: str, ttl_seconds: int = 86400
) -> None:
    """
    Lưu fingerprint vào Redis với TTL mặc định 24 giờ.

    Args:
        client:      Redis client (có thể None)
        fingerprint: SHA-256 fingerprint string
        ttl_seconds: Thời gian tồn tại (giây), mặc định 86400 = 24h
    """
    if client is None:
        return
    try:
        client.setex(f"dedup:{fingerprint}", ttl_seconds, "1")
    except Exception as exc:
        logger.debug("[DeduplicationPipeline] Redis SETEX lỗi: %s", exc)


def _check_score_exists_in_db(
    *,
    session: Any,
    university_id: Any,
    major_id: Any,
    year: int,
    admission_method: str,
    subject_combination: str,
) -> bool:
    """
    Kiểm tra bản ghi điểm chuẩn đã tồn tại trong DB chưa.

    Dùng ScoreRepository.find_by_composite_key() để query.

    Args:
        session:            SQLAlchemy session
        university_id:      UUID của trường
        major_id:           UUID của ngành
        year:               Năm tuyển sinh
        admission_method:   Phương thức xét tuyển
        subject_combination: Tổ hợp môn

    Returns:
        True nếu đã tồn tại, False nếu chưa.
    """
    try:
        from db.repositories.score_repo import ScoreRepository

        repo = ScoreRepository(session)
        existing = repo.find_by_composite_key(
            university_id=university_id,
            major_id=major_id,
            year=year,
            admission_method=admission_method,
            subject_combination=subject_combination,
        )
        return existing is not None
    except Exception as exc:
        logger.warning("[DeduplicationPipeline] _check_score_exists_in_db lỗi: %s", exc)
        return False
