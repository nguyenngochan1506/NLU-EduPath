# Kiến trúc & Công nghệ – Hệ thống Thu thập Dữ liệu

**Phần:** 02 / 09  
**Liên quan:** [README](./README.md) | [← 01 Tổng quan](./01_tong_quan_va_du_lieu.md) | [→ 03 Database Schema](./03_database_schema.md)

---

## 4. Kiến trúc hệ thống thu thập

### 4.1 Sơ đồ kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                        CRAWL SYSTEM                             │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Scheduler   │───►│  Job Queue   │───►│  Spider Manager  │   │
│  │ (APScheduler │    │  (Celery +   │    │  (Scrapy Engine) │   │
│  │   / Cron)    │    │   Redis)     │    │                  │   │
│  └──────────────┘    └──────────────┘    └────────┬─────────┘   │
│                                                   │             │
│                              ┌────────────────────┤             │
│                              │                    │             │
│                    ┌─────────▼──────┐  ┌──────────▼──────────┐  │
│                    │ Scrapy Spider  │  │ Playwright Spider   │  │
│                    │ (Static HTML)  │  │ (Dynamic/JS Pages)  │  │
│                    └─────────┬──────┘  └──────────┬──────────┘  │
│                              └──────────┬──────────┘            │
│                                         │                       │
│                              ┌──────────▼──────────┐            │
│                              │    Item Pipeline    │            │
│                              │  1. Validation      │            │
│                              │  2. Deduplication   │            │
│                              │  3. Normalization   │            │
│                              │  4. Enrichment      │            │
│                              └──────────┬──────────┘            │
│                                         │                       │
│                    ┌────────────────────┼─────────────────┐     │
│                    │                    │                  │     │
│           ┌────────▼───────┐  ┌────────▼──────┐  ┌───────▼──┐  │
│           │  PostgreSQL DB │  │  Redis Cache  │  │  Log DB  │  │
│           │  (main store)  │  │  (temp/cache) │  │(MongoDB) │  │
│           └────────────────┘  └───────────────┘  └──────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │                                   ▲
           ▼                                   │
  ┌─────────────────┐              ┌───────────────────┐
  │   AI Engine     │              │  Admin Dashboard  │
  │ (Recommendation │              │  (Monitor &       │
  │    Module)      │              │   Control UI)     │
  └─────────────────┘              └───────────────────┘
```

### 4.2 Luồng xử lý dữ liệu (Data Flow)

```
Bước 1: TRIGGER
  Admin nhấn "Chạy ngay" HOẶC Scheduler tự động kích hoạt
          │
          ▼
Bước 2: JOB DISPATCH
  Celery tạo task và đưa vào hàng đợi Redis
          │
          ▼
Bước 3: CRAWL
  Spider thu thập HTML/JSON từ các trang nguồn
          │
          ▼
Bước 4: PARSE
  Trích xuất dữ liệu thô (raw items) từ HTML
          │
          ▼
Bước 5: VALIDATE
  Kiểm tra tính đầy đủ, đúng kiểu, đúng format
          │
          ├── FAIL ──► Ghi vào error_log, bỏ qua bản ghi
          │
          ▼ PASS
Bước 6: DEDUPLICATE
  Kiểm tra trùng lặp theo composite key
          │
          ├── DUPLICATE ──► Cập nhật nếu có thay đổi, bỏ qua nếu giống
          │
          ▼ NEW
Bước 7: NORMALIZE
  Chuẩn hóa tên trường, tên ngành, mã ngành, tổ hợp môn
          │
          ▼
Bước 8: ENRICH
  Tự động mapping Holland types & Career Anchors cho ngành
          │
          ▼
Bước 9: STORE
  Lưu vào PostgreSQL, cập nhật Redis cache
          │
          ▼
Bước 10: NOTIFY
  Ghi log thành công, gửi thông báo cho Admin
```

---

## 5. Công nghệ & Tech Stack

### 5.1 Core Technologies

| Component | Công nghệ | Phiên bản | Lý do chọn |
|-----------|-----------|-----------|------------|
| **Ngôn ngữ chính** | Python | 3.11+ | Hệ sinh thái scraping phong phú nhất |
| **Framework Scraping** | Scrapy | 2.11+ | Hiệu năng cao, middleware linh hoạt, pipeline rõ ràng |
| **Dynamic Pages** | Playwright | 1.40+ | Xử lý JavaScript rendering tốt hơn Selenium |
| **HTML Parsing** | BeautifulSoup4 / lxml | latest | Fallback khi không dùng Scrapy selector |
| **Task Queue** | Celery | 5.3+ | Async job, retry tự động, monitoring |
| **Message Broker** | Redis | 7.0+ | Nhanh, nhẹ, phù hợp task queue |
| **Database chính** | PostgreSQL | 15+ | Dữ liệu quan hệ, query phức tạp, hỗ trợ UUID & JSONB |
| **Log Storage** | MongoDB | 7.0+ | Lưu log linh hoạt, schema-less |
| **Scheduler** | APScheduler | 3.10+ | Tích hợp Python app, cron-like |
| **Data Validation** | Pydantic | 2.0+ | Type-safe validation, auto docs |
| **ORM** | SQLAlchemy | 2.0+ | Tương thích nhiều DB, migration tốt |
| **Migration** | Alembic | latest | Quản lý schema DB theo version |
| **HTTP Client** | httpx | latest | Async, proxy support tốt |
| **Proxy Rotation** | scrapy-rotating-proxies | latest | Tránh bị block IP |

### 5.2 Cấu trúc thư mục dự án Crawl

```
craw-data/
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml
│
├── config/
│   ├── __init__.py
│   ├── settings.py               # Cấu hình chung (DB, Redis, logging)
│   ├── spider_config.py          # Cấu hình từng spider (selectors, URLs)
│   └── holland_mapping.py        # Bảng mapping Holland types → ngành
│
├── spiders/
│   ├── __init__.py
│   ├── base_spider.py            # Base class chung (retry, logging, rate limit)
│   ├── university_spider.py      # Crawl thông tin trường ĐH
│   ├── admission_score_spider.py # Crawl điểm chuẩn lịch sử
│   ├── major_info_spider.py      # Crawl thông tin ngành học
│   ├── job_market_spider.py      # Crawl thị trường lao động (static)
│   └── dynamic/
│       ├── __init__.py
│       ├── topcv_spider.py       # Playwright spider cho TopCV
│       └── vietnamworks_spider.py
│
├── pipelines/
│   ├── __init__.py
│   ├── validation_pipeline.py    # Bước 5: Validate item
│   ├── dedup_pipeline.py         # Bước 6: Deduplication
│   ├── normalization_pipeline.py # Bước 7: Normalize (tên, mã, tổ hợp)
│   ├── enrichment_pipeline.py    # Bước 8: Enrich – auto Holland mapping
│   └── storage_pipeline.py       # Bước 9: Lưu vào PostgreSQL
│
├── models/
│   ├── __init__.py
│   ├── university.py             # Pydantic schema + SQLAlchemy model
│   ├── major.py
│   ├── admission_score.py
│   ├── job_market.py
│   └── crawl_log.py
│
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py             # Khởi tạo Celery app
│   ├── crawl_tasks.py            # Task definitions (trigger, retry)
│   └── scheduler.py              # APScheduler setup & cron jobs
│
├── utils/
│   ├── __init__.py
│   ├── normalizer.py             # Chuẩn hóa tên trường, mã ngành, tổ hợp môn
│   ├── proxy_manager.py          # Quản lý proxy pool
│   ├── logger.py                 # Logging utilities
│   └── health_check.py           # Kiểm tra trạng thái crawler
│
├── db/
│   ├── __init__.py
│   ├── connection.py             # Kết nối PostgreSQL qua SQLAlchemy
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── university_repo.py
│   │   ├── major_repo.py
│   │   ├── score_repo.py
│   │   └── job_market_repo.py
│   └── migrations/
│       ├── env.py
│       ├── script.py.mako
│       └── versions/             # Alembic migration files
│
├── tests/
│   ├── conftest.py
│   ├── test_spiders/
│   │   ├── test_admission_score_spider.py
│   │   └── test_university_spider.py
│   ├── test_pipelines/
│   │   ├── test_validation_pipeline.py
│   │   ├── test_dedup_pipeline.py
│   │   └── test_normalization_pipeline.py
│   └── test_utils/
│       └── test_normalizer.py
│
└── scripts/
    ├── seed_universities.py      # Seed danh sách 50 trường ban đầu
    ├── seed_majors.py            # Seed danh sách mã ngành chuẩn Bộ GD&ĐT
    ├── run_all_spiders.py        # Chạy toàn bộ spiders thủ công
    └── data_quality_report.py   # Báo cáo chất lượng dữ liệu sau crawl
```

---

*← [01 Tổng quan & Dữ liệu](./01_tong_quan_va_du_lieu.md) | [03 Database Schema →](./03_database_schema.md)*