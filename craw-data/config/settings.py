import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ============================================================
# PROJECT IDENTITY
# ============================================================
BOT_NAME = "nlu-edupath-crawler"
SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

# ============================================================
# DATABASE
# ============================================================
_DB_USER = os.getenv("POSTGRES_USER", "crawler")
_DB_PASS = os.getenv("POSTGRES_PASSWORD", "crawler_pass")
_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
_DB_PORT = os.getenv("POSTGRES_PORT", "5432")
_DB_NAME = os.getenv("POSTGRES_DB", "nlu_edupath")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{_DB_USER}:{_DB_PASS}@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}",
)

# ============================================================
# REDIS
# ============================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ============================================================
# CRAWL BEHAVIOR
# ============================================================
# Respect robots.txt
ROBOTSTXT_OBEY = False  # Nhiều trang giáo dục VN không có robots.txt chuẩn

# Delay giữa các request (giây) – tránh bị block
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "1.5"))

# Số request đồng thời
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "8"))
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN", "4"))

# AutoThrottle – tự động điều chỉnh tốc độ dựa trên response time
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Retry
RETRY_ENABLED = True
RETRY_TIMES = int(os.getenv("MAX_RETRY", "3"))
RETRY_HTTP_CODES = [500, 502, 503, 504, 429, 408]

# Timeout
DOWNLOAD_TIMEOUT = 30

# ============================================================
# USER AGENT
# ============================================================
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Thêm header mặc định để trông như browser thật
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}

# ============================================================
# PLAYWRIGHT (scrapy-playwright)
# ============================================================
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = os.getenv("PLAYWRIGHT_BROWSER_TYPE", "chromium")
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true",
    "args": [
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
    ],
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = int(
    os.getenv("PLAYWRIGHT_DEFAULT_TIMEOUT", "15000")
)
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1920, "height": 1080},
        "locale": "vi-VN",
        "user_agent": USER_AGENT,
        "java_script_enabled": True,
        "ignore_https_errors": True,
    }
}

# ============================================================
# ITEM PIPELINES
# Thứ tự xử lý: Validate → Normalize → Dedup → Store
# ============================================================
ITEM_PIPELINES = {
    "pipelines.validation_pipeline.ValidationPipeline": 100,
    "pipelines.normalization_pipeline.NormalizationPipeline": 200,
    "pipelines.dedup_pipeline.DeduplicationPipeline": 300,
    "pipelines.storage_pipeline.StoragePipeline": 400,
}

# ============================================================
# MIDDLEWARES
# ============================================================
DOWNLOADER_MIDDLEWARES = {
    # Tắt built-in User-Agent middleware, dùng custom header
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

SPIDER_MIDDLEWARES = {
    "scrapy.spidermiddlewares.httperror.HttpErrorMiddleware": 50,
}

# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# Ghi log ra file (Tắt để xem trực tiếp trong terminal)
# _log_dir = BASE_DIR / os.getenv("LOG_DIR", "logs")
# _log_dir.mkdir(exist_ok=True)
# LOG_FILE = str(_log_dir / "scrapy.log")

# ============================================================
# FEEDS (output tạm cho debug)
# Tắt khi chạy production – dùng StoragePipeline thay thế
# ============================================================
# FEEDS = {
#     "data/output/%(name)s_%(time)s.jsonl": {"format": "jsonlines"},
# }

# ============================================================
# EXTENSIONS
# ============================================================
EXTENSIONS = {
    "scrapy.extensions.corestats.CoreStats": 500,
    "scrapy.extensions.telnet.TelnetConsole": None,  # Tắt telnet để bảo mật
}

# ============================================================
# SPIDER-SPECIFIC CONFIG
# ============================================================
SCORE_YEAR_FROM = int(os.getenv("SCORE_YEAR_FROM", "2020"))
SCORE_YEAR_TO = int(os.getenv("SCORE_YEAR_TO", "2025"))

# ============================================================
# MISC
# ============================================================
# Không lưu cookie giữa các request (stateless crawling)
COOKIES_ENABLED = False

# Giới hạn độ sâu crawl để tránh vô tình crawl quá sâu
DEPTH_LIMIT = 5

# Tắt telnet console (security)
TELNETCONSOLE_ENABLED = False
