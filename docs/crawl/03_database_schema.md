# 03 – Thiết kế Database Schema

**Thuộc về:** [Kế hoạch Thu thập Dữ liệu – NLU-EduPath](./README.md)  
**Use Case liên quan:** UC06 – Cấu hình & Kích hoạt Web Scraping  

---

## Mục lục

- [6.1 ERD Tổng quát](#61-erd-tổng-quát)
- [6.2 Lý do dùng UUID](#62-lý-do-dùng-uuid)
- [6.3 Chi tiết từng bảng](#63-chi-tiết-từng-bảng)
- [6.4 Index tối ưu truy vấn](#64-index-tối-ưu-truy-vấn)

---

## 6.1 ERD Tổng quát

```
universities ──< admission_scores >── majors
     │                                   │
     │                              major_holland_mapping
     │                                   │
     └──────────── university_majors ────┘
                                         │
                                    job_categories
                                         │
                                  major_job_mapping
```

---

## 6.2 Lý do dùng UUID

| Tiêu chí | SERIAL (auto-increment) | UUID v4 |
|----------|------------------------|---------|
| Phân tán / merge dữ liệu nhiều nguồn | ❌ Xung đột ID | ✅ Không bao giờ trùng |
| Bảo mật (không đoán được ID tiếp theo) | ❌ Dễ đoán | ✅ Ngẫu nhiên hoàn toàn |
| Tạo ID phía client (spider) trước khi insert | ❌ Phải chờ DB | ✅ Spider tự sinh UUID |
| Hiệu năng index | ✅ Nhỏ gọn (4 bytes) | ⚠️ Lớn hơn (16 bytes) – chấp nhận được |

> **Kết luận:** UUID là lựa chọn phù hợp cho hệ thống crawl đa nguồn, nơi dữ liệu được tổng hợp từ nhiều spider độc lập và cần tránh xung đột ID khi merge.

Kích hoạt extension trên PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- gen_random_uuid() có sẵn từ PostgreSQL 13+ mà không cần extension
```

---

## 6.3 Chi tiết từng bảng

### Bảng 1: `universities`

Lưu thông tin cơ bản và tuyển sinh của từng trường đại học.

```sql
CREATE TABLE universities (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    university_code  VARCHAR(20) UNIQUE NOT NULL,  -- Mã do Bộ GD&ĐT cấp (VD: QSB, BKA)
    name             VARCHAR(300) NOT NULL,
    short_name       VARCHAR(50),                  -- VD: HUST, UEH, NEU
    university_type  VARCHAR(20)  CHECK (university_type IN ('public', 'private', 'foreign_affiliated')),
    region           VARCHAR(10)  CHECK (region IN ('north', 'central', 'south')),
    province         VARCHAR(100),
    address          TEXT,
    website          VARCHAR(500),
    admission_url    VARCHAR(500),
    logo_url         VARCHAR(500),
    tuition_min      BIGINT,                        -- VNĐ/năm
    tuition_max      BIGINT,
    established_year SMALLINT,
    is_active        BOOLEAN     DEFAULT TRUE,
    scraped_at       TIMESTAMP   NOT NULL,
    source_url       VARCHAR(500),
    created_at       TIMESTAMP   DEFAULT NOW(),
    updated_at       TIMESTAMP   DEFAULT NOW()
);
```

---

### Bảng 2: `majors`

Lưu thông tin ngành học, bao gồm mapping Holland RIASEC và Career Anchors phục vụ AI.

```sql
CREATE TABLE majors (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    major_code          VARCHAR(20) UNIQUE NOT NULL,  -- Mã ngành chuẩn Bộ GD&ĐT (VD: 7480201)
    name                VARCHAR(300) NOT NULL,
    major_group         VARCHAR(100),                  -- Tên khối ngành (VD: Kỹ thuật, Kinh tế)
    major_group_code    VARCHAR(10),                   -- Mã khối ngành
    description         TEXT,
    career_options      JSONB       DEFAULT '[]',      -- ["Lập trình viên", "Business Analyst", ...]
    required_skills     JSONB       DEFAULT '[]',      -- ["Python", "Toán cao cấp", ...]
    subject_combinations JSONB      DEFAULT '[]',      -- ["A00", "A01", "D01"]
    holland_types       JSONB       DEFAULT '[]',      -- ["I", "R", "C"]  ← dùng cho AI engine
    career_anchor_tags  JSONB       DEFAULT '[]',      -- ["Technical/Functional Competence"]
    study_duration      SMALLINT    DEFAULT 4,         -- Số năm đào tạo
    degree_level        VARCHAR(20) DEFAULT 'bachelor' CHECK (degree_level IN ('bachelor', 'engineer', 'master')),
    is_active           BOOLEAN     DEFAULT TRUE,
    scraped_at          TIMESTAMP   NOT NULL,
    source_url          VARCHAR(500),
    created_at          TIMESTAMP   DEFAULT NOW(),
    updated_at          TIMESTAMP   DEFAULT NOW()
);
```

---

### Bảng 3: `admission_scores`

Lưu điểm chuẩn lịch sử theo từng năm, trường, ngành và tổ hợp môn.

```sql
CREATE TABLE admission_scores (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id       UUID        NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    major_id            UUID        NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    year                SMALLINT    NOT NULL,          -- Năm tuyển sinh (VD: 2024)
    admission_method    VARCHAR(100),                  -- "THPT", "Học bạ", "ĐGNL", "SAT"
    subject_combination VARCHAR(10),                   -- "A00", "A01", "D01", ...
    cutoff_score        NUMERIC(5, 2),                 -- Điểm chuẩn (thang 30)
    quota               INT,                           -- Chỉ tiêu xét tuyển
    note                TEXT,                          -- Ghi chú (điểm ưu tiên, v.v.)
    scraped_at          TIMESTAMP   NOT NULL,
    source_url          VARCHAR(500),
    created_at          TIMESTAMP   DEFAULT NOW(),

    -- Đảm bảo không trùng bản ghi cho cùng trường/ngành/năm/phương thức/tổ hợp
    UNIQUE (university_id, major_id, year, admission_method, subject_combination)
);
```

---

### Bảng 4: `job_categories`

Lưu dữ liệu thị trường lao động theo nhóm nghề, phục vụ tính năng "Tra cứu thị trường" (UC09).

```sql
CREATE TABLE job_categories (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(200) NOT NULL,            -- Tên nhóm nghề (VD: "Lập trình Backend")
    related_majors   JSONB       DEFAULT '[]',         -- [major_code, ...] các ngành liên quan
    avg_salary_min   BIGINT,                           -- Lương trung bình thấp nhất (VNĐ/tháng)
    avg_salary_max   BIGINT,                           -- Lương trung bình cao nhất
    median_salary    BIGINT,                           -- Lương trung vị
    demand_level     VARCHAR(20) CHECK (demand_level IN ('low', 'medium', 'high', 'very_high')),
    growth_trend     VARCHAR(20) CHECK (growth_trend IN ('declining', 'stable', 'growing', 'booming')),
    top_skills       JSONB       DEFAULT '[]',         -- ["Python", "Docker", "AWS", ...]
    job_count_sample INT,                              -- Số tin tuyển dụng mẫu tại thời điểm crawl
    source           VARCHAR(100),                     -- "topcv" | "vietnamworks" | "careerbuilder"
    scraped_at       TIMESTAMP   NOT NULL,
    created_at       TIMESTAMP   DEFAULT NOW(),
    updated_at       TIMESTAMP   DEFAULT NOW()
);
```

---

### Bảng 5: `crawl_logs`

Nhật ký mỗi lần chạy spider, hiển thị trên Admin Dashboard (UC06).

```sql
CREATE TABLE crawl_logs (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    spider_name      VARCHAR(100) NOT NULL,            -- "admission_score_spider", "university_spider", ...
    status           VARCHAR(20) CHECK (status IN ('running', 'success', 'failed', 'partial')),
    started_at       TIMESTAMP   NOT NULL,
    finished_at      TIMESTAMP,
    records_new      INT         DEFAULT 0,            -- Số bản ghi được thêm mới
    records_updated  INT         DEFAULT 0,            -- Số bản ghi được cập nhật
    records_failed   INT         DEFAULT 0,            -- Số bản ghi bị lỗi / bỏ qua
    error_summary    TEXT,                             -- Tóm tắt lỗi (nếu có)
    triggered_by     VARCHAR(100)                      -- "scheduler" hoặc "admin:<user_uuid>"
);
```

---

### Bảng 6: `university_majors` *(join table)*

Liên kết trường đại học với các ngành học mà trường đó đào tạo.

```sql
CREATE TABLE university_majors (
    university_id  UUID  NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    major_id       UUID  NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
    PRIMARY KEY (university_id, major_id)
);
```

---

## 6.4 Index tối ưu truy vấn

```sql
-- Tra cứu điểm chuẩn theo năm (dùng nhiều nhất)
CREATE INDEX idx_scores_year
    ON admission_scores(year);

-- Tra cứu điểm chuẩn theo trường + ngành
CREATE INDEX idx_scores_university_major
    ON admission_scores(university_id, major_id);

-- Lọc ngành theo khối ngành (dùng trong AI engine)
CREATE INDEX idx_majors_group_code
    ON majors(major_group_code);

-- Lọc trường theo khu vực + tỉnh thành (dùng trong bộ lọc học phí/khu vực)
CREATE INDEX idx_universities_region_province
    ON universities(region, province);

-- Tra cứu log crawl theo tên spider và thời gian
CREATE INDEX idx_crawl_logs_spider_started
    ON crawl_logs(spider_name, started_at DESC);

-- Tìm kiếm ngành theo holland_types (GIN index cho JSONB)
CREATE INDEX idx_majors_holland_types
    ON majors USING GIN (holland_types);

-- Tìm kiếm nhóm nghề theo kỹ năng (GIN index cho JSONB)
CREATE INDEX idx_job_categories_top_skills
    ON job_categories USING GIN (top_skills);
```

---

## Ghi chú triển khai

| Hạng mục | Chi tiết |
|----------|----------|
| **Migration tool** | Alembic – mỗi thay đổi schema tạo một revision file riêng |
| **Môi trường** | PostgreSQL 15+ (hỗ trợ `gen_random_uuid()` native) |
| **ORM** | SQLAlchemy 2.0 với kiểu `UUID` mapped sang `uuid.UUID` trong Python |
| **Seed data** | Chạy `scripts/seed_data.py` sau migration để nạp dữ liệu trường và ngành ban đầu |
| **Rollback** | Mỗi Alembic revision có hàm `downgrade()` để rollback an toàn |

---

*Quay lại: [README – Tổng quan kế hoạch](./README.md)*