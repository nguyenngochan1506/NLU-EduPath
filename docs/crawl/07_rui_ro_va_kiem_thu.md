# 07 – Quản lý Rủi ro & Kế hoạch Test

**Tài liệu thuộc dự án:** NLU-EduPath – Hệ thống Hướng nghiệp & Gợi ý Ngành học  
**Phần liên quan:** UC06 – Cấu hình & Kích hoạt Web Scraping

← [06 – Data Pipeline](./06_data_pipeline.md) | [08 – Timeline & DoD](./08_timeline_va_dod.md) →

---

## Mục lục

- [12. Quản lý Rủi ro](#12-quản-lý-rủi-ro)
- [13. Kế hoạch Test](#13-kế-hoạch-test)
  - [13.1 Unit Test – Pipeline](#131-unit-test--pipeline)
  - [13.2 Integration Test – Spider](#132-integration-test--spider)
  - [13.3 Data Quality Test](#133-data-quality-test)

---

## 12. Quản lý Rủi ro

| # | Rủi ro | Xác suất | Mức độ ảnh hưởng | Biện pháp phòng ngừa | Biện pháp xử lý |
|---|--------|----------|-----------------|----------------------|-----------------|
| R01 | Website nguồn thay đổi cấu trúc HTML | Cao | Cao | Tách toàn bộ selector ra `config/spider_config.py`, không hardcode trong spider | Cập nhật selector, ghi chú version thay đổi vào Git commit |
| R02 | Bị block IP (anti-bot) | Trung bình | Cao | Rate limiting, User-Agent rotation, random delay giữa các request | Kích hoạt proxy pool, giảm tốc độ crawl |
| R03 | Dữ liệu không nhất quán giữa các nguồn | Cao | Trung bình | Validation chặt, dùng mã chuẩn Bộ GD&ĐT làm khóa chính | Admin review và hiệu chỉnh qua UC20 |
| R04 | Website nguồn ngừng hoạt động | Thấp | Cao | Luôn có ≥ 2 nguồn backup cho mỗi loại dữ liệu | Chuyển toàn bộ traffic sang nguồn backup |
| R05 | Dữ liệu lỗi làm AI recommend sai | Thấp | Rất Cao | Validation nghiêm ngặt, Admin review và approve trước khi publish | Rollback về snapshot dữ liệu trước đó |
| R06 | Vi phạm ToS của website nguồn | Trung bình | Trung bình | Đọc và tuân thủ `robots.txt`, không crawl dữ liệu cá nhân, giữ rate limit thấp | Dừng crawl nguồn đó, tìm nguồn thay thế hợp lệ |
| R07 | Thiếu dữ liệu ngành/điểm chuẩn mới nhất (2025) | Trung bình | Trung bình | Lên lịch crawl sát mùa tuyển sinh (tháng 3–7) | Nhập thủ công cho các ngành còn thiếu |

### Mức độ tổng hợp

```
          Xác suất
    Cao   │ R01 ─────────────── R03
          │           R06
  T.Bình  │      R02
          │                     R07
    Thấp  │           R04  R05
          └─────────────────────────────
               Thấp  T.Bình  Cao  Rất Cao
                          Mức độ ảnh hưởng
```

> **Ưu tiên xử lý:** R05 (dù xác suất thấp nhưng ảnh hưởng tới chất lượng AI) → R01 → R02

---

## 13. Kế hoạch Test

### 13.1 Unit Test – Pipeline

Các test case tập trung vào từng pipeline độc lập, dùng dữ liệu giả (mock/fixture).

| Test Case | Mô tả | Input mẫu | Kết quả kỳ vọng |
|-----------|-------|-----------|-----------------|
| `test_validation_valid_score` | Điểm chuẩn hợp lệ | `{score: 25.5, combination: "A00", year: 2024}` | ✅ Pass, item được chuyển tiếp |
| `test_validation_score_out_of_range` | Điểm chuẩn vượt thang 30 | `{score: 35.0}` | ❌ Fail, ghi error log, drop item |
| `test_validation_score_too_low` | Điểm chuẩn bất hợp lệ | `{score: 5.0}` | ❌ Fail, ghi error log, drop item |
| `test_validation_missing_required` | Thiếu trường bắt buộc | `{year: 2024}` (thiếu `university_id`) | ❌ Fail, ghi error log |
| `test_validation_invalid_url` | URL không hợp lệ | `{source_url: "not-a-url"}` | ❌ Fail Rule V07 |
| `test_dedup_new_record` | Bản ghi chưa tồn tại trong DB | Bản ghi mới hoàn toàn | ✅ Cho phép tiếp tục StoragePipeline |
| `test_dedup_exact_duplicate` | Bản ghi đã tồn tại, giá trị giống hệt | Trùng composite key + giá trị | ⏭️ Bỏ qua, không update |
| `test_dedup_updated_value` | Trùng key nhưng điểm chuẩn thay đổi | Trùng key, `cutoff_score` khác | 🔄 Update bản ghi cũ |
| `test_normalization_subject_combo` | Chuẩn hóa chuỗi tổ hợp môn | `"Toán - Lý - Hóa"` | `"A00"` |
| `test_normalization_university_name` | Chuẩn hóa tên trường về mã chuẩn | `"ĐH Bách Khoa - HN"` | `university_code = "BKA"` |
| `test_holland_mapping_engineering` | Mapping Holland cho ngành kỹ thuật | Ngành `"Kỹ thuật phần mềm"` | `holland_types` chứa `"I"`, `"R"` |
| `test_holland_mapping_economics` | Mapping Holland cho ngành kinh tế | Ngành `"Kinh doanh quốc tế"` | `holland_types` chứa `"E"`, `"C"` |
| `test_holland_mapping_arts` | Mapping Holland cho ngành nghệ thuật | Ngành `"Thiết kế đồ họa"` | `holland_types` chứa `"A"` |

**Cách chạy:**

```
cd craw-data/
pytest tests/test_pipelines/ -v --tb=short
```

**Target coverage:** ≥ 80% cho mỗi pipeline module.

---

### 13.2 Integration Test – Spider

Các test case kiểm tra spider hoạt động đúng với môi trường thực tế (hoặc HTML fixture lưu sẵn).

| Test Case | Mô tả | Điều kiện | Kết quả kỳ vọng |
|-----------|-------|-----------|-----------------|
| `test_spider_http_200` | Spider gọi URL thực, nhận HTTP 200 | Có kết nối Internet | Response status 200, body không rỗng |
| `test_spider_parse_score_table` | Parse bảng điểm chuẩn từ HTML fixture | File HTML lưu sẵn | ≥ 1 `AdmissionScoreItem` được sinh ra |
| `test_spider_parse_university_info` | Parse trang thông tin trường từ HTML fixture | File HTML lưu sẵn | `UniversityItem` có đủ các trường bắt buộc |
| `test_spider_retry_on_503` | Giả lập server trả HTTP 503 | Mock server | Spider retry đúng 3 lần, sau đó ghi log FAILED |
| `test_spider_retry_backoff` | Kiểm tra thời gian giữa các lần retry | Mock server 503 | Delay lần 2 > delay lần 1 (exponential backoff) |
| `test_spider_rate_limit` | Đo thời gian giữa 2 request liên tiếp | Live hoặc mock | Khoảng cách ≥ `DOWNLOAD_DELAY` trong config |
| `test_spider_playwright_render` | Playwright render trang JS trước khi parse | Có kết nối Internet | Element xuất hiện trong DOM sau khi chờ |
| `test_spider_log_on_start` | Spider tự ghi vào `crawl_logs` khi khởi động | DB test | Có bản ghi `status = "running"` trong bảng `crawl_logs` |
| `test_spider_log_on_finish` | Spider cập nhật log khi hoàn tất | DB test | Bản ghi `crawl_logs` cập nhật `status = "success"` |

**Lưu ý khi viết test spider:**

- Lưu HTML fixture vào `tests/fixtures/html/` để test không phụ thuộc Internet.
- Dùng `pytest-httpx` hoặc `responses` để mock HTTP call.
- Dùng database test riêng biệt (SQLite in-memory hoặc PostgreSQL test schema).

**Cách chạy:**

```
cd craw-data/
pytest tests/test_spiders/ -v --tb=short -m "not live"
```

> Thêm marker `@pytest.mark.live` cho test cần Internet thật, chạy riêng khi cần.

---

### 13.3 Data Quality Test

Chạy `scripts/data_quality_report.py` sau **mỗi lần crawl** để đảm bảo dữ liệu đạt chuẩn trước khi AI sử dụng.

**Các chỉ số theo dõi:**

| Chỉ số | Mô tả | Target | Hành động nếu fail |
|--------|-------|--------|--------------------|
| `valid_rate` | % bản ghi pass toàn bộ validation rules | ≥ 95% | Gửi cảnh báo Admin, dừng publish |
| `holland_coverage` | % ngành có `holland_types` được điền | ≥ 95% | Chạy lại EnrichmentPipeline |
| `university_score_coverage` | % trường có ít nhất 1 bản ghi điểm chuẩn | ≥ 85% | Chạy lại AdmissionScoreSpider cho trường thiếu |
| `major_description_rate` | % ngành có `description` không rỗng | ≥ 90% | Ghi danh sách ngành thiếu vào log |
| `subject_combo_coverage` | % ngành có `subject_combinations` không rỗng | ≥ 95% | Xem lại MajorInfoSpider |
| `duplicate_rate` | % bản ghi bị trùng lặp (nếu có) | = 0% | Chạy lại DeduplicationPipeline |
| `salary_data_coverage` | % nhóm nghề có dữ liệu lương | ≥ 80% | Chạy lại JobMarketSpider |

**Ví dụ output report:**

```
============================================================
  DATA QUALITY REPORT – NLU-EduPath Crawl System
  Generated: 2025-06-01 02:15:00
============================================================

[universities]
  Tổng số trường:           214
  Có đầy đủ thông tin:      197 / 214 (92.1%)  ✅

[majors]
  Tổng số ngành:            531
  Có holland_types:         522 / 531 (98.3%)  ✅
  Có description:           476 / 531 (89.6%)  ⚠️  (target: ≥ 90%)
  Có subject_combinations:  515 / 531 (97.0%)  ✅

[admission_scores]
  Tổng bản ghi:           12,847
  Bản ghi hợp lệ:         12,541 / 12,847 (97.6%)  ✅
  Bản ghi trùng lặp:           0  ✅
  Trường có điểm chuẩn:      198 / 214 (92.5%)  ✅

[job_categories]
  Tổng nhóm nghề:             57
  Có dữ liệu lương:           51 / 57 (89.5%)  ✅

============================================================
  KẾT LUẬN: ⚠️  CẢNH BÁO – 1 chỉ số chưa đạt target
  → major_description_rate: 89.6% < 90% (target)
  → Hành động: Xem danh sách ngành thiếu tại logs/missing_descriptions.txt
============================================================
```

**Cách chạy thủ công:**

```
cd craw-data/
python scripts/data_quality_report.py --output logs/quality_$(date +%Y%m%d).txt
```

---

*← [06 – Data Pipeline](./06_data_pipeline.md) | [08 – Timeline & DoD](./08_timeline_va_dod.md) →*

*Tài liệu thuộc bộ kế hoạch thu thập dữ liệu – NLU-EduPath 2025–2026*