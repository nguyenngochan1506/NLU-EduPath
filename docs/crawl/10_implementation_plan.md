# 10 – Kế hoạch Triển khai Chi tiết: Thu thập Dữ liệu (Implementation Plan)

Mục đích: chuyển các hướng dẫn và thiết kế thành các bước thực thi cụ thể, có lệnh kiểm tra, trách nhiệm và tiêu chí chấp nhận để hoàn thành phần thu thập dữ liệu (Sprint 0 + Sprint 1 đã hoàn thành). Tài liệu này đặt tại docs/crawl để đội phát triển và giảng viên dễ theo dõi.

---

## Tóm tắt ngắn

- Phạm vi: Triển khai crawler để thu thập điểm chuẩn 2020–2025, seed dữ liệu universities/majors, đảm bảo pipeline validation → normalize → dedup → store hoạt động.
- Kết quả mong đợi: Bảng `admission_scores` có dữ liệu sạch ≥ 2,000 bản ghi; pipelines pass unit tests; scheduler có thể trigger manual/run.
- Thời gian: Sprint 0 (hoàn thành) + Sprint 1 (hoàn thành). Tài liệu này dùng để vận hành và lặp cải tiến.

---

## 1. Yêu cầu tiền đề (Prerequisites)

- Docker & docker-compose, hoặc Python 3.11 local venv
- PostgreSQL (cấu hình trong `craw-data/config/settings.py` hoặc biến môi trường)
- Redis (nếu sử dụng Celery)
- Node/chromium nếu chạy Playwright (cần cài playwright và browser binaries)
- Các file seed đã có: `craw-data/scripts/seed_data.py` chứa UNIVERSITIES_SEED và MAJORS_SEED

---

## 2. Môi trường & Khởi tạo (one-time)

1. Build & up cơ bản bằng Docker (recommended):

   cd craw-data && docker-compose up -d --build

2. Tạo virtualenv (nếu không dùng Docker):

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install  # nếu cần

3. Áp migration DB (Alembic):

   cd craw-data && alembic upgrade head

4. Seed dữ liệu universities + majors (local hoặc container):

   cd craw-data && python scripts/seed_data.py --only universities
   cd craw-data && python scripts/seed_data.py --only majors

5. Kiểm tra kết nối DB:

   psql -h <host> -U <user> -d <db> -c "SELECT count(*) FROM universities;"

---

## 3. Triển khai Spider thử nghiệm (smoke-test)

Mục tiêu: chạy nhanh spider trên một tập nhỏ để xác thực selectors, pipelines và storage.

1. Chạy AdmissionScoreSpider nguồn MOET với 3 trường sample:

   cd craw-data && scrapy crawl admission_score -a source=moet -a university_codes=QSB,BKA,QSE -o sample_moet.jsonl -t jsonlines

2. Kiểm tra output JSONL hoặc DB:

   jq -s 'length' sample_moet.jsonl  # số bản ghi
   psql -c "SELECT COUNT(*) FROM admission_scores WHERE scraped_at > now() - interval '1 day';"

3. Nếu dùng tuyensinh247 (Playwright):

   cd craw-data && scrapy crawl admission_score -a source=tuyensinh247 -a years=2023 -a university_codes=QSB -o sample_ts247.jsonl -t jsonlines

4. Fix selectors nếu cần: cập nhật `craw-data/config/spider_config.py` → chỉnh selector tương ứng → lặp lại step 1.

---

## 4. Command list để chạy production-run (toàn bộ seed 50 trường, 2020–2025)

- Chạy toàn bộ MOET (tất cả năm):

  cd craw-data && scrapy crawl admission_score -a source=moet

- Chạy toàn bộ tuyensinh247 (chi tiết; Playwright):

  cd craw-data && scrapy crawl admission_score -a source=tuyensinh247

- Tùy chọn giới hạn năm/university_codes để chạy từng phần:

  scrapy crawl admission_score -a source=moet -a years=2020,2021 -a university_codes=QSB,QSE

---

## 5. Validation, Normalization, Deduplication & Storage — Checklist

- [x] ValidationPipeline: kiểm tra bắt buộc và Pydantic validation (`craw-data/pipelines/validation_pipeline.py`).
- [x] NormalizationPipeline: chuẩn hóa tên ngành & tổ hợp môn (`craw-data/pipelines/normalization_pipeline.py`).
- [x] DedupPipeline: session-level và DB-level dedup (`craw-data/pipelines/dedup_pipeline.py`).
- [x] StoragePipeline: lưu vào Postgres, mapping FK (`craw-data/pipelines/storage_pipeline.py`).
- Test command: cd craw-data && pytest -q craw-data/tests/test_pipelines

Acceptance rule: sau chạy full job, `records_failed / total_records <= 5%` và duplicate rate gần 0%.

---

## 6. Data Quality & Reporting

- Sử dụng `craw-data/scripts/data_quality_report.py` để sinh báo cáo (counts, failed reasons, duplicates, missing majors).
- Mẫu lệnh:

  cd craw-data && python scripts/data_quality_report.py --db-url postgresql://user:pass@host:5432/dbname --since 2025-01-01

- Output: CSV/JSON report lưu trong `craw-data/reports/` (tự tạo) và gửi cho Admin review.

---

## 7. Acceptance Criteria (DoD) cho Sprint 1

- DB phải có ≥ 2,000 bản ghi admission_scores hợp lệ.
- Data Quality Report: tỷ lệ `valid ≥ 95%` hoặc lỗi đã được chấp nhận và ghi chú.
- Unit tests cho validation & normalization phải pass.
- Admin có thể trigger crawl manual và read crawl_logs (endpoint hoặc DB).

---

## 8. Lịch & Phân công ngắn hạn (giai đoạn vận hành)

- Người thực hiện chính (Dev Lead): kiểm tra selectors, run full crawl, fix lỗi mapping.
- Dev 1: Kiểm tra pipeline & storage, sửa migration nếu cần.
- Dev 2: Chạy data quality report, điều chỉnh normalization rules.

---

## 9. Giám sát & Recovery

- Bảng `crawl_logs` ghi lại mỗi job: status, started_at, finished_at, records_new, records_failed, error_summary.
- Cảnh báo tự động: nếu spider fail 3 lần liên tiếp hoặc `records_failed > 10%` → thông báo Admin (email/Zalo).
- Recovery: sửa selector → rerun job cho phạm vi ảnh hưởng (`years`, `university_codes`).

---

## 10. Ghi chú vận hành ngắn (tips)

- Khi chạy tuyensinh247, bật playwright và đảm bảo browser binaries đã cài (`playwright install`).
- Test với small set (3–5 trường) trước khi chạy toàn bộ 50 trường.
- Khi gặp dữ liệu major không tìm thấy `major_code`, lưu vào bảng `pending_major_review` để Admin xử lý thủ công.

---

## 11. Tài liệu liên quan

- `docs/crawl/01_tong_quan_va_du_lieu.md`
- `docs/crawl/04_thiet_ke_module.md`
- `docs/crawl/06_data_pipeline.md`
- `craw-data/config/spider_config.py`
- `craw-data/scripts/seed_data.py`
- `craw-data/spiders/admission_score_spider.py`

---

Nếu muốn, có thể bổ sung checklist CI/CD (GitHub Actions) để tự động chạy unit tests và smoke-test spider trên PR trước khi merge.
