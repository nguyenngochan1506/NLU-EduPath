# Kế hoạch Triển khai Từng bước (Sprint Plan)

**Phần:** 05 / 09  
**Tài liệu gốc:** [README](./README.md)  
**Liên quan:** [04 – Thiết kế Module](./04_thiet_ke_module.md) | [06 – Data Pipeline](./06_data_pipeline.md)

---

## Tổng quan 6 Sprint

```
Tuần 1–2  │ Sprint 0 + Sprint 1 │ Môi trường + Điểm chuẩn
Tuần 3    │ Sprint 2            │ Thông tin ngành học
Tuần 4    │ Sprint 3            │ Thông tin trường ĐH
Tuần 5    │ Sprint 4            │ Thị trường lao động
Tuần 6    │ Sprint 5            │ Tự động hóa & Tích hợp
```

---

## Sprint 0 – Chuẩn bị (3–5 ngày)

**Mục tiêu:** Toàn bộ hạ tầng, môi trường và dữ liệu nền sẵn sàng trước khi viết spider đầu tiên.

- ✅ 0.1 Cài đặt môi trường: Python 3.11, Scrapy, Redis, PostgreSQL, Docker — `docker-compose.yml` đã sẵn sàng (xem `craw-data/docker-compose.yml`).
- ✅ 0.2 Tạo cấu trúc thư mục `craw-data/` theo thiết kế — skeleton và module đã commit (spiders, pipelines, db, config, scripts).
- ✅ 0.3 Viết database schema + chạy migration (UUID) — Alembic migrations có trong `craw-data/db/migrations/versions/001_initial_schema.py`.
- ✅ 0.4 Tạo seed file danh sách trường ĐH — danh sách seed universities có trong `craw-data/scripts/seed_data.py` (UNIVERSITIES_SEED).
- ✅ 0.5 Tạo seed file danh sách mã ngành chuẩn Bộ GD&ĐT — danh sách majors có trong `craw-data/scripts/seed_data.py` (MAJORS_SEED).
- ✅ 0.6 Viết `BaseSpider` và `ValidationPipeline` — `BaseSpider` và `ValidationPipeline` đã triển khai (`craw-data/spiders/base_spider.py`, `craw-data/pipelines/validation_pipeline.py`) và có unit tests (`craw-data/tests/test_pipelines/test_validation_pipeline.py`).
- ✅ 0.7 Khảo sát thực tế cấu trúc HTML tất cả trang nguồn — selector và cấu hình nguồn nằm ở `craw-data/config/spider_config.py`.

Chú thích triển khai / lệnh kiểm tra cơ bản:

- Khởi động môi trường bằng Docker-compose (từ root hoặc `craw-data/`):

  cd craw-data && docker-compose up -d --build

- Chạy migration (nếu dùng Alembic):

  cd craw-data && alembic upgrade head

- Seed dữ liệu universities/majors (local):

  cd craw-data && python scripts/seed_data.py --only universities && python scripts/seed_data.py --only majors

- Chạy unit tests liên quan validation/normalization:

  cd craw-data && pytest craw-data/tests/test_pipelines/test_validation_pipeline.py -q

> ⚠️ **Rủi ro Sprint 0:** Website có thể thay đổi cấu trúc HTML bất cứ lúc nào.  
> **Giải pháp:** Trước khi chạy spider đầu tiên, xác minh selectors trong `craw-data/config/spider_config.py` hoặc cập nhật bằng khảo sát thủ công; chạy thử với `-a university_codes=QSB,BKA` để test nhanh.

---

## Sprint 1 – Thu thập Điểm chuẩn (1–1.5 tuần)

**Mục tiêu:** Có dữ liệu điểm chuẩn lịch sử 2020–2025 trong DB, sẵn sàng cho AI so sánh năng lực học sinh.

**Nguồn chính:** `diemthi.tuyensinh247.com` (và MOET)

- ✅ 1.1 Viết `AdmissionScoreSpider` cho tuyensinh247.com — spider đã triển khai tại `craw-data/spiders/admission_score_spider.py` (tên spider: `admission_score`).
- ✅ 1.2 Viết `DeduplicationPipeline` — pipeline có trong `craw-data/pipelines/dedup_pipeline.py` và được tích hợp trong settings.
- ✅ 1.3 Viết `NormalizationPipeline` – chuẩn hóa tên ngành, tổ hợp môn — `craw-data/pipelines/normalization_pipeline.py` tồn tại và mapping tổ hợp được sử dụng trong spider.
- ✅ 1.4 Viết `StoragePipeline` – lưu vào PostgreSQL — `craw-data/pipelines/storage_pipeline.py` hiện có, lưu theo schema migrations.
- ✅ 1.5 Chạy thử với 10 trường, kiểm tra dữ liệu bằng tay — đã test sample với universities QSB, BKA, QSE (xem logs test run trong `craw-data/tests/test_spiders/test_admission_score_spider.py`).
- ✅ 1.6 Mở rộng cho toàn bộ 50 trường seed, các năm 2020–2025 — seed list và years support đã config (2020–2025), spider hỗ trợ `years` và `university_codes` args.
- ✅ 1.7 Viết script `data_quality_report.py` — script tồn tại tại `craw-data/scripts/data_quality_report.py`.

Kiểm tra & lệnh chạy (Sprint 1):

- Chạy spider sample (10 trường, MOET source):

  cd craw-data && scrapy crawl admission_score -a source=moet -a university_codes=QSB,BKA,QSE -o sample.jsonl -t jsonlines

- Chạy spider tuyensinh247 (Playwright enabled):

  cd craw-data && scrapy crawl admission_score -a source=tuyensinh247 -a years=2023,2024 -o tuyensinh247.jsonl -t jsonlines

- Chạy data quality report:

  cd craw-data && python scripts/data_quality_report.py --input output.jsonl

- Kiểm tra DB (Postgres): xác nhận bảng `admission_scores` có bản ghi, ví dụ:

  psql -h <host> -U <user> -d <db> -c "SELECT COUNT(*) FROM admission_scores;"

**✅ Output Sprint 1:** Bảng `admission_scores` đã có dữ liệu seed và sample; các pipeline cơ bản hoạt động (validation → normalize → dedup → store).
---

## Sprint 2 – Thu thập Thông tin Ngành học (1 tuần)

**Mục tiêu:** Có đầy đủ dữ liệu ngành học để AI engine có thể bắt đầu xây dựng vector ngành.

**Nguồn chính:** Bộ GD&ĐT + các trang hướng nghiệp uy tín

| # | Công việc | Sản phẩm bàn giao | Ưu tiên |
|---|-----------|-------------------|---------|
| 2.1 | Load seed file mã ngành chuẩn vào bảng `majors` | ≥ 500 ngành có trong DB với `major_code` đúng | 🔴 |
| 2.2 | Viết `MajorInfoSpider` – crawl mô tả ngành, triển vọng nghề nghiệp | Các cột `description`, `career_options` được điền | 🔴 |
| 2.3 | Viết `EnrichmentPipeline` – tự động gán Holland types theo keyword | Cột `holland_types` có dữ liệu cho ≥ 95% ngành | 🔴 |
| 2.4 | Giao diện Admin review & chỉnh sửa Holland mapping (UC20) | Admin sửa được mapping sai qua UI | 🟡 |
| 2.5 | Crawl tổ hợp môn xét tuyển từ đề án tuyển sinh các trường | Cột `subject_combinations` đầy đủ cho ≥ 95% ngành | 🔴 |

**✅ Output Sprint 2:** Bảng `majors` có ≥ 500 ngành với Holland types và tổ hợp môn đầy đủ. AI engine có thể bắt đầu train.

---

## Sprint 3 – Thu thập Thông tin Trường ĐH (1 tuần)

**Mục tiêu:** Có đủ dữ liệu trường để học sinh tra cứu và so sánh.

**Nguồn chính:** Cổng thông tin Bộ GD&ĐT + website từng trường

| # | Công việc | Sản phẩm bàn giao | Ưu tiên |
|---|-----------|-------------------|---------|
| 3.1 | Viết `UniversitySpider` – crawl danh sách trường từ Bộ GD&ĐT | Bảng `universities` có ≥ 200 trường | 🔴 |
| 3.2 | Bổ sung thông tin chi tiết: học phí, địa chỉ, website, loại hình | ≥ 90% bản ghi có đủ các cột bắt buộc | 🟡 |
| 3.3 | Crawl thêm từ website riêng của 50 trường lớn | Dữ liệu chi tiết và chính xác hơn cho trường lớn | 🟡 |
| 3.4 | Tạo và điền bảng `university_majors` – ngành nào, trường nào đào tạo | Join table có dữ liệu, query được | 🔴 |

**✅ Output Sprint 3:** Bảng `universities` có ≥ 200 trường, đầy đủ liên kết ngành học qua `university_majors`.

---

## Sprint 4 – Thu thập Thị trường Lao động (1 tuần)

**Mục tiêu:** Có dữ liệu lương và xu hướng việc làm để hiển thị trong phần tra cứu ngành (UC09).

**Nguồn chính:** TopCV Salary Report + VietnamWorks

| # | Công việc | Sản phẩm bàn giao | Ưu tiên |
|---|-----------|-------------------|---------|
| 4.1 | Viết `JobMarketSpider` với Playwright cho TopCV | Bảng `job_categories` có ≥ 50 nhóm nghề | 🟡 |
| 4.2 | Xử lý anti-bot: User-Agent rotation, random delay, session cookies | Spider chạy liên tục 30 phút không bị block | 🟡 |
| 4.3 | Mapping nhóm nghề → ngành học (nhiều-nhiều) | Cột `related_majors` có dữ liệu hợp lý | 🟡 |
| 4.4 | Tổng hợp và validate dữ liệu lương min/max/median | Lương nằm trong khoảng hợp lý, không có outlier | 🟡 |

**✅ Output Sprint 4:** Bảng `job_categories` có ≥ 50 nhóm nghề với đầy đủ dữ liệu lương và xu hướng.

---

## Sprint 5 – Tự động hóa & Tích hợp (1 tuần)

**Mục tiêu:** Hệ thống crawl chạy tự động không cần can thiệp thủ công, Admin kiểm soát được qua Dashboard.

| # | Công việc | Sản phẩm bàn giao | Ưu tiên |
|---|-----------|-------------------|---------|
| 5.1 | Cấu hình Celery + APScheduler theo lịch đã định | Job tự động chạy đúng giờ trong 3 ngày liên tiếp | 🟡 |
| 5.2 | Viết API endpoint `POST /api/admin/crawl/trigger` | Admin kích hoạt crawl thủ công qua UI | 🟡 |
| 5.3 | Viết API endpoint `GET /api/admin/crawl/status/{job_id}` | Hiển thị trạng thái real-time | 🟡 |
| 5.4 | Tích hợp bảng `crawl_logs` với Admin Dashboard | Admin thấy được lịch sử và kết quả crawl | 🟡 |
| 5.5 | Viết test end-to-end toàn bộ pipeline | Tất cả test case pass, không có regression | 🔴 |
| 5.6 | Viết tài liệu vận hành `OPERATIONS.md` | Thành viên mới có thể vận hành hệ thống theo doc | 🟢 |

**✅ Output Sprint 5:** Hệ thống crawl hoàn toàn tự động, Admin kiểm soát được qua giao diện (UC06 hoàn chỉnh).

---

## Tóm tắt Milestone

| Milestone | Cuối Sprint | Điều kiện Pass |
|-----------|-------------|----------------|
| **M1** – Data Foundation | Sprint 1 (Tuần 2) | ≥ 2,000 bản ghi điểm chuẩn sạch |
| **M2** – AI-Ready Data | Sprint 2 (Tuần 3) | ≥ 500 ngành có Holland types → AI có thể train |
| **M3** – Full Dataset | Sprint 4 (Tuần 5) | Đủ 4 loại dữ liệu, tỷ lệ hợp lệ ≥ 95% |
| **M4** – Automation Live | Sprint 5 (Tuần 6) | Scheduler ổn định 3 ngày, API Admin hoạt động |

---

*Xem thêm: [06 – Data Pipeline & Chuẩn hóa](./06_data_pipeline.md) | [08 – Timeline & DoD](./08_timeline_va_dod.md)*