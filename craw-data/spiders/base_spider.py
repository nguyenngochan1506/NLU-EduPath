# ============================================================
# spiders/base_spider.py
# BaseSpider – Lớp cha chung cho tất cả spider trong hệ thống
#
# Tính năng:
#   - Tự động cấu hình rate limiting, retry, User-Agent rotation
#   - Logging chuẩn hóa với spider name và context
#   - Hỗ trợ cả static HTML (Scrapy) và dynamic JS (Playwright)
#   - Ghi crawl_log vào DB khi bắt đầu / kết thúc
#   - Fingerprint-based request deduplication (tùy chọn)
#   - Health check trước khi crawl
#
# Cách dùng:
#   class MySpider(BaseSpider):
#       name = "my_spider"
#       allowed_domains = ["example.com"]
#
#       def parse(self, response):
#           ...
# ============================================================

from __future__ import annotations

import hashlib
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Generator, Iterator, Optional
from urllib.parse import urlencode, urljoin

import scrapy
from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured
from scrapy.http import Request, Response
from scrapy.utils.project import get_project_settings


logger = logging.getLogger(__name__)


class BaseSpider(scrapy.Spider):
    """
    Lớp cha cho tất cả spider trong hệ thống NLU-EduPath.

    Tính năng chính:
    ─────────────────
    1. User-Agent rotation       – Xoay vòng UA để tránh bị block
    2. Rate limiting             – download_delay tùy chỉnh mỗi spider
    3. Retry thông minh          – Ghi nhận và log request thất bại
    4. Crawl log tracking        – Ghi log vào DB qua CrawlLog model
    5. Playwright support        – Tự động thêm meta khi cần JS rendering
    6. Request fingerprinting    – Tránh crawl URL trùng trong cùng session
    7. Stats tracking            – Đếm items hợp lệ / lỗi / skip

    Thuộc tính cần override trong spider con:
    ─────────────────────────────────────────
        name (str)                  : Tên spider (bắt buộc)
        start_urls (list[str])      : URL khởi đầu (hoặc override start_requests)
        allowed_domains (list[str]) : Giới hạn domain được crawl

    Thuộc tính tùy chọn (có thể override):
    ────────────────────────────────────────
        requires_playwright (bool)  : True nếu cần Playwright (mặc định False)
        download_delay (float)      : Giây chờ giữa request (mặc định 1.5)
        max_retries (int)           : Số lần retry tối đa (mặc định 3)
        source_name (str)           : Tên nguồn dữ liệu để ghi log
        triggered_by (str)          : "scheduler" | "admin:<uuid>"
    """

    # ── Phải override trong spider con ──────────────────────
    name: str = "base_spider"

    # ── Có thể override ─────────────────────────────────────
    requires_playwright: bool = False
    download_delay: float = 1.5
    max_retries: int = 3
    source_name: str = "unknown"
    triggered_by: str = "scheduler"

    # ── Internal ─────────────────────────────────────────────
    _crawl_log_id: Optional[uuid.UUID] = None
    _seen_fingerprints: set[str]
    _stats: dict[str, int]
    _start_time: datetime

    # ============================================================
    # LIFECYCLE HOOKS
    # ============================================================

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Đọc kwargs từ command line hoặc Celery task
        self.triggered_by = kwargs.get("triggered_by", self.triggered_by)
        self.source_name = kwargs.get("source_name", self.source_name)

        # Khởi tạo tracking
        self._seen_fingerprints = set()
        self._stats = {
            "items_scraped": 0,
            "items_dropped": 0,
            "requests_made": 0,
            "requests_failed": 0,
            "requests_retried": 0,
            "pages_visited": 0,
        }
        self._start_time = datetime.now(tz=timezone.utc)

        self.logger.info(
            "[%s] Khởi tạo spider | source=%s | triggered_by=%s",
            self.name,
            self.source_name,
            self.triggered_by,
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        Factory method của Scrapy – kết nối spider với crawler.
        Đăng ký signal handlers tại đây.
        """
        spider = super().from_crawler(crawler, *args, **kwargs)

        # Kết nối signal để tracking thống kê
        crawler.signals.connect(spider._on_item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(spider._on_item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(spider._on_spider_error, signal=signals.spider_error)

        return spider

    def start_requests(self) -> Iterator[Request]:
        """
        Override start_requests để tự động inject Playwright meta
        nếu requires_playwright = True.

        Spider con có thể override method này để tùy chỉnh request đầu tiên.
        """
        self.logger.info(
            "[%s] Bắt đầu crawl %d URL | Playwright=%s",
            self.name,
            len(self.start_urls),
            self.requires_playwright,
        )

        for url in self.start_urls:
            yield self._make_request(
                url=url,
                callback=self.parse,
                priority=0,
            )

    # ============================================================
    # REQUEST FACTORY
    # ============================================================

    def _make_request(
        self,
        url: str,
        callback,
        method: str = "GET",
        headers: Optional[dict] = None,
        body: Optional[str] = None,
        meta: Optional[dict] = None,
        priority: int = 0,
        dont_filter: bool = False,
        cb_kwargs: Optional[dict] = None,
        wait_for_selector: Optional[str] = None,
        wait_until: Optional[str] = None,
        wait_timeout_ms: int = 15000,
        playwright_page_methods: Optional[list] = None,
    ) -> Request:
        """
        Factory tạo Scrapy Request với đầy đủ cấu hình.

        Tự động:
        - Thêm User-Agent ngẫu nhiên từ pool
        - Thêm meta Playwright nếu requires_playwright = True
        - Thêm fingerprint tracking

        Args:
            url:                  URL cần crawl
            callback:             Hàm parse response
            method:               HTTP method (GET/POST)
            headers:              Headers bổ sung
            meta:                 Scrapy request meta
            priority:             Độ ưu tiên request (cao hơn = xử lý trước)
            dont_filter:          True để bỏ qua dedup filter của Scrapy
            cb_kwargs:            Keyword arguments truyền vào callback
            wait_for_selector:    CSS selector chờ khi dùng Playwright
            wait_timeout_ms:      Timeout Playwright (ms)
            playwright_page_methods: Danh sách PageMethod cho Playwright

        Returns:
            scrapy.http.Request đã cấu hình đầy đủ
        """
        request_meta = meta or {}

        # ── Playwright ──────────────────────────────────────────
        if self.requires_playwright:
            request_meta["playwright"] = True
            request_meta["playwright_context"] = "default"

            page_methods = playwright_page_methods or []

            if wait_for_selector:
                try:
                    from scrapy_playwright.page import PageMethod
                    page_methods.insert(
                        0,
                        PageMethod(
                            "wait_for_selector",
                            wait_for_selector,
                            timeout=wait_timeout_ms,
                        ),
                    )
                except ImportError:
                    self.logger.warning(
                        "[%s] scrapy-playwright chưa cài – bỏ qua wait_for_selector.",
                        self.name,
                    )

            if wait_until:
                try:
                    from scrapy_playwright.page import PageMethod
                    page_methods.append(
                        PageMethod("wait_until", wait_until)
                    )
                except ImportError:
                    pass

            if page_methods:
                request_meta["playwright_page_methods"] = page_methods

            # Playwright cần errback để xử lý lỗi timeout
            errback = self._handle_playwright_error
        else:
            errback = self._handle_request_error

        # ── Headers ──────────────────────────────────────────────
        default_headers = {
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "User-Agent": self._get_random_user_agent(),
        }
        if headers:
            default_headers.update(headers)

        # ── Tracking meta ────────────────────────────────────────
        request_meta.setdefault("retry_count", 0)
        request_meta.setdefault("spider_name", self.name)

        return Request(
            url=url,
            callback=callback,
            method=method,
            headers=default_headers,
            body=body,
            meta=request_meta,
            priority=priority,
            dont_filter=dont_filter,
            cb_kwargs=cb_kwargs or {},
            errback=errback,
        )

    def _make_playwright_request(
        self,
        url: str,
        callback,
        wait_for_selector: Optional[str] = None,
        wait_timeout_ms: int = 15000,
        scroll_to_bottom: bool = False,
        **kwargs,
    ) -> Request:
        """
        Shortcut để tạo request Playwright với các tùy chọn thường dùng.

        Args:
            url:               URL cần crawl
            callback:          Hàm parse response
            wait_for_selector: CSS selector cần chờ trước khi extract
            wait_timeout_ms:   Timeout (ms) cho wait_for_selector
            scroll_to_bottom:  Tự động scroll xuống cuối trang (lazy load)
        """
        page_methods = []

        try:
            from scrapy_playwright.page import PageMethod

            if wait_for_selector:
                page_methods.append(
                    PageMethod(
                        "wait_for_selector",
                        wait_for_selector,
                        timeout=wait_timeout_ms,
                    )
                )

            if scroll_to_bottom:
                # Scroll xuống để trigger lazy loading
                page_methods.append(
                    PageMethod(
                        "evaluate",
                        "window.scrollTo(0, document.body.scrollHeight)",
                    )
                )
                # Chờ thêm sau khi scroll
                page_methods.append(PageMethod("wait_for_timeout", 1500))

        except ImportError:
            self.logger.warning(
                "[%s] scrapy-playwright chưa cài – PageMethod bị bỏ qua.",
                self.name,
            )

        # Override requires_playwright tạm thời nếu spider gốc không dùng Playwright
        original = self.requires_playwright
        self.requires_playwright = True
        request = self._make_request(
            url=url,
            callback=callback,
            playwright_page_methods=page_methods,
            wait_for_selector=wait_for_selector,
            wait_timeout_ms=wait_timeout_ms,
            **kwargs,
        )
        self.requires_playwright = original
        return request

    # ============================================================
    # ERROR HANDLERS
    # ============================================================

    def _handle_request_error(self, failure) -> None:
        """
        Errback chung cho request HTTP thất bại.
        Ghi log và tăng counter stats.
        """
        request = failure.request
        self._stats["requests_failed"] += 1

        self.logger.error(
            "[%s] Request thất bại | URL=%s | Lỗi=%s",
            self.name,
            request.url,
            repr(failure.value),
        )

    def _handle_playwright_error(self, failure) -> None:
        """
        Errback cho Playwright request thất bại.
        Phân biệt lỗi timeout với lỗi mạng để log phù hợp.
        """
        request = failure.request
        self._stats["requests_failed"] += 1

        error_type = type(failure.value).__name__
        self.logger.error(
            "[%s] Playwright request thất bại | URL=%s | Type=%s | Lỗi=%s",
            self.name,
            request.url,
            error_type,
            str(failure.value)[:200],  # Giới hạn độ dài log
        )

    # ============================================================
    # SIGNAL HANDLERS
    # ============================================================

    def _on_item_scraped(self, item, response, spider) -> None:
        """Tăng counter khi item được scraped thành công."""
        if spider.name == self.name:
            self._stats["items_scraped"] += 1

    def _on_item_dropped(self, item, response, exception, spider) -> None:
        """Tăng counter khi item bị drop bởi pipeline."""
        if spider.name == self.name:
            self._stats["items_dropped"] += 1

    def _on_spider_error(self, failure, response, spider) -> None:
        """Log lỗi từ spider callback."""
        if spider.name == self.name:
            self._stats["requests_failed"] += 1
            self.logger.error(
                "[%s] Spider callback lỗi | URL=%s | %s",
                self.name,
                response.url if response else "N/A",
                repr(failure.value),
            )

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def _get_random_user_agent(self) -> str:
        """
        Lấy User-Agent ngẫu nhiên từ pool trong spider_config.py.
        Fallback về UA mặc định nếu không load được config.
        """
        try:
            from config.spider_config import USER_AGENTS

            return random.choice(USER_AGENTS)
        except (ImportError, IndexError):
            return (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

    def _make_fingerprint(self, *parts: str) -> str:
        """
        Tạo SHA-256 fingerprint từ các phần tử chuỗi.
        Dùng để dedup request/item trong cùng session crawl.

        Args:
            *parts: Các chuỗi cần hash, VD: (university_code, major_name, year)

        Returns:
            Chuỗi hex 16 ký tự (đủ ngắn để lưu trong set)
        """
        key = "|".join(str(p).strip().lower() for p in parts)
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _is_seen(self, *parts: str) -> bool:
        """
        Kiểm tra fingerprint đã tồn tại chưa.
        Nếu chưa → thêm vào set và trả về False.
        Nếu rồi → trả về True (bỏ qua item).
        """
        fp = self._make_fingerprint(*parts)
        if fp in self._seen_fingerprints:
            return True
        self._seen_fingerprints.add(fp)
        return False

    def _mark_seen(self, *parts: str) -> None:
        """Đánh dấu fingerprint đã thấy (không kiểm tra duplicate)."""
        fp = self._make_fingerprint(*parts)
        self._seen_fingerprints.add(fp)

    def _clean_text(self, raw: Optional[str]) -> Optional[str]:
        """
        Làm sạch văn bản thô từ HTML:
        - Xóa whitespace thừa đầu/cuối
        - Gộp nhiều space/newline thành một
        - Trả về None nếu chuỗi rỗng sau khi làm sạch
        """
        if raw is None:
            return None
        import re
        cleaned = re.sub(r"\s+", " ", raw).strip()
        return cleaned if cleaned else None

    def _extract_text(
        self,
        selector,
        css: Optional[str] = None,
        xpath: Optional[str] = None,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract và làm sạch text từ một selector.

        Args:
            selector: Scrapy Selector object (response hoặc element)
            css:      CSS selector string
            xpath:    XPath selector string
            default:  Giá trị mặc định nếu không tìm thấy

        Returns:
            Text đã làm sạch hoặc default
        """
        try:
            if css:
                raw = selector.css(css).get(default="")
            elif xpath:
                raw = selector.xpath(xpath).get(default="")
            else:
                return default

            # Strip HTML tags nếu có
            import re
            text = re.sub(r"<[^>]+>", "", raw or "")
            result = self._clean_text(text)
            return result if result else default
        except Exception:
            return default

    def _extract_texts(
        self,
        selector,
        css: Optional[str] = None,
        xpath: Optional[str] = None,
    ) -> list[str]:
        """
        Extract danh sách text từ một selector (getall).

        Returns:
            Danh sách text đã làm sạch, bỏ qua phần tử rỗng
        """
        try:
            import re

            if css:
                raws = selector.css(css).getall()
            elif xpath:
                raws = selector.xpath(xpath).getall()
            else:
                return []

            result = []
            for raw in raws:
                text = re.sub(r"<[^>]+>", "", raw or "")
                cleaned = self._clean_text(text)
                if cleaned:
                    result.append(cleaned)
            return result
        except Exception:
            return []

    def _extract_attr(
        self,
        selector,
        css: str,
        attr: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract giá trị attribute (href, src, etc.) từ CSS selector.

        Args:
            selector: Scrapy Selector
            css:      CSS selector
            attr:     Tên attribute cần lấy
            default:  Giá trị mặc định

        Returns:
            Giá trị attribute đã strip hoặc default
        """
        try:
            val = selector.css(f"{css}::attr({attr})").get(default=default)
            return val.strip() if val else default
        except Exception:
            return default

    def _absolute_url(self, response: Response, relative_url: str) -> str:
        """
        Chuyển URL tương đối thành URL tuyệt đối dựa trên base URL của response.

        Args:
            response:     Scrapy Response hiện tại
            relative_url: URL tương đối (VD: "/diem-chuan/2024")

        Returns:
            URL tuyệt đối (VD: "https://example.com/diem-chuan/2024")
        """
        if not relative_url:
            return response.url
        if relative_url.startswith(("http://", "https://")):
            return relative_url
        return urljoin(response.url, relative_url)

    def _random_delay(self, base: float = 1.0, jitter: float = 0.5) -> None:
        """
        Dừng một khoảng thời gian ngẫu nhiên để simulate human behavior.
        Chỉ dùng trong các context đồng bộ (không phải trong callback Scrapy).

        Args:
            base:   Thời gian cơ bản (giây)
            jitter: Biên động ngẫu nhiên thêm vào (giây)
        """
        delay = base + random.uniform(0, jitter)
        time.sleep(delay)

    def _now_utc(self) -> datetime:
        """Trả về thời điểm hiện tại với timezone UTC."""
        return datetime.now(tz=timezone.utc)

    def _log_parse_start(self, response: Response, context: str = "") -> None:
        """Log bắt đầu parse một URL."""
        self._stats["pages_visited"] += 1
        self.logger.debug(
            "[%s] Parse #%d | URL=%s %s",
            self.name,
            self._stats["pages_visited"],
            response.url,
            f"| {context}" if context else "",
        )

    def _log_item_yield(self, item_type: str, key: str = "") -> None:
        """Log khi yield một item."""
        self.logger.debug(
            "[%s] Yield %s %s",
            self.name,
            item_type,
            f"| key={key}" if key else "",
        )

    def _log_skip(self, reason: str, url: str = "") -> None:
        """Log khi bỏ qua một URL/item."""
        self.logger.debug(
            "[%s] Skip | reason=%s %s",
            self.name,
            reason,
            f"| url={url}" if url else "",
        )

    # ============================================================
    # CRAWL LOG INTEGRATION
    # ============================================================

    def _init_crawl_log(self) -> Optional[uuid.UUID]:
        """
        Tạo bản ghi CrawlLog ở DB khi spider bắt đầu chạy.
        Trả về UUID của log entry để cập nhật sau khi kết thúc.
        Trả về None nếu không kết nối được DB (không fail spider).
        """
        try:
            from db.connection import get_session
            from models.crawl_log import CrawlLog

            log_id = uuid.uuid4()
            with get_session() as session:
                log = CrawlLog(
                    id=log_id,
                    spider_name=self.name,
                    status="running",
                    started_at=self._start_time,
                    records_new=0,
                    records_updated=0,
                    records_failed=0,
                    triggered_by=self.triggered_by,
                )
                session.add(log)

            self.logger.info(
                "[%s] CrawlLog tạo thành công | id=%s",
                self.name,
                log_id,
            )
            return log_id

        except Exception as exc:
            self.logger.warning(
                "[%s] Không tạo được CrawlLog (DB chưa sẵn sàng?): %s",
                self.name,
                exc,
            )
            return None

    def _finalize_crawl_log(
        self,
        log_id: Optional[uuid.UUID],
        status: str,
        error_summary: Optional[str] = None,
    ) -> None:
        """
        Cập nhật CrawlLog khi spider kết thúc.

        Args:
            log_id:        UUID của CrawlLog entry (từ _init_crawl_log)
            status:        "success" | "failed" | "partial"
            error_summary: Tóm tắt lỗi nếu có
        """
        if log_id is None:
            return

        try:
            from db.connection import get_session
            from models.crawl_log import CrawlLog

            finished_at = self._now_utc()

            with get_session() as session:
                log = session.get(CrawlLog, log_id)
                if log:
                    log.status = status
                    log.finished_at = finished_at
                    log.records_new = self._stats.get("items_scraped", 0)
                    log.records_failed = self._stats.get("items_dropped", 0)
                    log.error_summary = error_summary

            duration = (finished_at - self._start_time).total_seconds()
            self.logger.info(
                "[%s] CrawlLog cập nhật | status=%s | duration=%.1fs | "
                "new=%d | failed=%d",
                self.name,
                status,
                duration,
                self._stats.get("items_scraped", 0),
                self._stats.get("items_dropped", 0),
            )

        except Exception as exc:
            self.logger.warning(
                "[%s] Không cập nhật được CrawlLog: %s",
                self.name,
                exc,
            )

    def open_spider(self, spider) -> None:
        """
        Hook được Scrapy gọi khi spider bắt đầu chạy.
        Khởi tạo CrawlLog trong DB.
        """
        self.logger.info(
            "[%s] ===== Spider BẮT ĐẦU | source=%s | triggered_by=%s =====",
            self.name,
            self.source_name,
            self.triggered_by,
        )
        self._crawl_log_id = self._init_crawl_log()

    def close_spider(self, spider) -> None:
        """
        Hook được Scrapy gọi khi spider kết thúc.
        Cập nhật CrawlLog với kết quả và thống kê.
        """
        # Xác định status dựa trên stats
        failed = self._stats.get("requests_failed", 0)
        scraped = self._stats.get("items_scraped", 0)

        if scraped == 0 and failed > 0:
            status = "failed"
        elif failed > 0 and scraped > 0:
            status = "partial"
        else:
            status = "success"

        self._finalize_crawl_log(
            log_id=self._crawl_log_id,
            status=status,
        )

        # In báo cáo tổng kết
        duration = (self._now_utc() - self._start_time).total_seconds()
        self.logger.info(
            "[%s] ===== Spider KẾT THÚC | status=%s | duration=%.1fs =====\n"
            "  Pages visited  : %d\n"
            "  Items scraped  : %d\n"
            "  Items dropped  : %d\n"
            "  Requests failed: %d\n"
            "  Requests retried: %d",
            self.name,
            status,
            duration,
            self._stats.get("pages_visited", 0),
            self._stats.get("items_scraped", 0),
            self._stats.get("items_dropped", 0),
            self._stats.get("requests_failed", 0),
            self._stats.get("requests_retried", 0),
        )

    # ============================================================
    # PAGINATION HELPERS
    # ============================================================

    def _next_page_request(
        self,
        response: Response,
        current_page: int,
        total_pages: int,
        callback,
        url_template: Optional[str] = None,
        page_param: str = "page",
        **cb_kwargs,
    ) -> Optional[Request]:
        """
        Tạo request cho trang tiếp theo nếu còn trang.

        Args:
            response:      Response hiện tại
            current_page:  Số trang hiện tại (1-based)
            total_pages:   Tổng số trang
            callback:      Callback function
            url_template:  Template URL với placeholder {page}
                           Nếu None → thêm query param vào URL hiện tại
            page_param:    Tên query param phân trang (mặc định "page")
            **cb_kwargs:   Keyword arguments truyền vào callback

        Returns:
            Request trang tiếp theo hoặc None nếu đã hết
        """
        next_page = current_page + 1
        if next_page > total_pages:
            self.logger.debug(
                "[%s] Đã crawl hết %d trang.",
                self.name,
                total_pages,
            )
            return None

        if url_template:
            next_url = url_template.format(page=next_page)
        else:
            # Thêm/cập nhật query param page trong URL hiện tại
            from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

            parsed = urlparse(response.url)
            params = parse_qs(parsed.query)
            params[page_param] = [str(next_page)]
            new_query = urlencode({k: v[0] for k, v in params.items()})
            next_url = urlunparse(parsed._replace(query=new_query))

        self.logger.debug(
            "[%s] Trang tiếp theo: %d/%d | URL=%s",
            self.name,
            next_page,
            total_pages,
            next_url,
        )

        return self._make_request(
            url=next_url,
            callback=callback,
            cb_kwargs={"page": next_page, "total_pages": total_pages, **cb_kwargs},
        )

    def _is_valid_score(self, raw_score) -> bool:
        """
        Kiểm tra nhanh xem raw_score có hợp lệ để parse không.
        Trả về False nếu là placeholder như "-", "---", "N/A".
        """
        if raw_score is None:
            return False
        s = str(raw_score).strip()
        return s not in ("", "-", "--", "---", "N/A", "n/a", "Chua co")
