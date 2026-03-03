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

| # | Công việc | Sản phẩm bàn giao | Người làm |
|---|-----------|-------------------|-----------|
| 0.1 | Cài đặt môi trường: Python 3.11, Scrapy, Redis, PostgreSQL, Docker | `docker-compose.yml` khởi động thành công | Cả nhóm |
| 0.2 | Tạo cấu trúc thư mục `craw-data/` theo thiết kế | Repo có đầy đủ skeleton, commit lên Git | Dev 1 |
| 0.3 | Viết database schema + chạy migration (UUID) | Migration file chạy thành công, bảng tạo đúng | Dev 2 |
| 0.4 | Tạo seed file danh sách 50 trường ĐH lớn | `scripts/seed_universities.json` | Cả nhóm |
| 0.5 | Tạo seed file danh sách mã ngành chuẩn Bộ GD&ĐT | `scripts/seed_majors.json` | Cả nhóm |
| 0.6 | Viết `BaseSpider` và `ValidationPipeline` | Unit test pass | Dev 1 |
| 0.7 | Khảo sát thực tế cấu trúc HTML tất cả trang nguồn | Tài liệu selectors cho từng trang, lưu vào `config/spider_config.py` | Dev 2 |

> ⚠️ **Rủi ro Sprint 0:** Website có thể thay đổi cấu trúc HTML bất cứ lúc nào.  
> **Giải pháp:** Dành nguyên 1 ngày khảo sát thực tế và ghi lại selectors trước khi viết bất kỳ dòng code spider nào.

---

## Sprint 1 – Thu thập Điểm chuẩn (1–1.5 tuần)

**Mục tiêu:** Có dữ liệu điểm chuẩn lịch sử 2020–2025 trong DB, sẵn sàng cho AI so sánh năng lực học sinh.

**Nguồn chính:** `diemthi.tuyensinh247.com`

| # | Công việc | Sản phẩm bàn giao | Ưu tiên |
|---|-----------|-------------------|---------|
| 1.1 | Viết `AdmissionScoreSpider` cho tuyensinh247.com | Spider chạy được, parse ra đúng item | 🔴 |
| 1.2 | Viết `DeduplicationPipeline` | Chạy 2 lần liên tiếp không tạo duplicate | 🔴 |
| 1.3 | Viết `NormalizationPipeline` – chuẩn hóa tên ngành, tổ hợp môn | "Toán – Lý – Hóa" → `A00`, tên ngành đồng nhất | 🔴 |
| 1.4 | Viết `StoragePipeline` – lưu vào PostgreSQL | Bản ghi xuất hiện trong bảng `admission_scores` | 🔴 |
| 1.5 | Chạy thử với 10 trường, kiểm tra dữ liệu bằng tay | Báo cáo data quality lần đầu | 🟡 |
| 1.6 | Mở rộng cho toàn bộ 50 trường seed, các năm 2020–2025 | ≥ 2,000 bản ghi điểm chuẩn trong DB | 🟡 |
| 1.7 | Viết script `data_quality_report.py` | Report in ra tỷ lệ hợp lệ / trùng / thiếu | 🟢 |

**✅ Output Sprint 1:** Bảng `admission_scores` có ≥ 2,000 bản ghi sạch, pass data quality report.

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