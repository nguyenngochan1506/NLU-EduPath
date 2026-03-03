# 08 – Timeline, Phân công & Tiêu chí Hoàn thành

**Phần của:** [Kế hoạch Thu thập Dữ liệu – NLU-EduPath](./README.md)

---

## 14. Timeline & Phân công

### 14.1 Timeline tổng thể

```
Tuần 1–2  (Sprint 0 + Sprint 1): Môi trường + Điểm chuẩn
Tuần 3    (Sprint 2):            Thông tin ngành học
Tuần 4    (Sprint 3):            Thông tin trường ĐH
Tuần 5    (Sprint 4):            Thị trường lao động
Tuần 6    (Sprint 5):            Tự động hóa & Tích hợp
```

### 14.2 Bảng phân công chi tiết

| Sprint | Task | Dev 1 | Dev 2 | Deadline |
|--------|------|-------|-------|----------|
| Sprint 0 | Cài đặt môi trường, Docker | ✅ | ✅ | Ngày 3 |
| Sprint 0 | Database schema + migration | | ✅ | Ngày 3 |
| Sprint 0 | BaseSpider + ValidationPipeline | ✅ | | Ngày 5 |
| Sprint 0 | Seed data (trường + ngành) | ✅ | ✅ | Ngày 5 |
| Sprint 1 | AdmissionScoreSpider | ✅ | | Tuần 1 cuối |
| Sprint 1 | DeduplicationPipeline | | ✅ | Tuần 1 cuối |
| Sprint 1 | NormalizationPipeline | ✅ | | Tuần 2 đầu |
| Sprint 1 | StoragePipeline + chạy thực tế | ✅ | ✅ | Tuần 2 cuối |
| Sprint 2 | MajorInfoSpider | | ✅ | Tuần 3 giữa |
| Sprint 2 | EnrichmentPipeline (Holland map) | ✅ | | Tuần 3 cuối |
| Sprint 3 | UniversitySpider | | ✅ | Tuần 4 cuối |
| Sprint 4 | JobMarketSpider (Playwright) | ✅ | | Tuần 5 cuối |
| Sprint 5 | Celery + APScheduler | | ✅ | Tuần 6 đầu |
| Sprint 5 | API endpoints cho Admin | ✅ | | Tuần 6 giữa |
| Sprint 5 | End-to-end test + Documentation | ✅ | ✅ | Tuần 6 cuối |

### 14.3 Mốc bàn giao (Milestones)

| Milestone | Thời điểm | Điều kiện pass | Sản phẩm bàn giao |
|-----------|-----------|----------------|-------------------|
| **M1** – Data foundation | Cuối tuần 2 | ≥ 2,000 bản ghi điểm chuẩn sạch | DB có dữ liệu, data quality report |
| **M2** – AI-ready data | Cuối tuần 3 | ≥ 500 ngành có Holland types | AI engine có thể bắt đầu train |
| **M3** – Full dataset | Cuối tuần 5 | Đủ 4 loại dữ liệu, tỷ lệ hợp lệ ≥ 95% | Dataset hoàn chỉnh |
| **M4** – Automation live | Cuối tuần 6 | Scheduler chạy ổn định 3 ngày liên tiếp | Hệ thống crawl tự động |

---

## 15. Tiêu chí Hoàn thành (Definition of Done)

### 15.1 Tiêu chí DoD cho từng Spider

Một spider được coi là **DONE** khi:

- [ ] Code đã được review bởi thành viên còn lại
- [ ] Unit test coverage ≥ 80% cho pipeline liên quan
- [ ] Chạy thành công trên môi trường local với dữ liệu thực
- [ ] Dữ liệu thu thập pass data quality report (tỷ lệ hợp lệ ≥ 95%)
- [ ] Không có duplicate trong DB sau khi chạy 2 lần liên tiếp
- [ ] Log ghi đầy đủ vào bảng `crawl_logs`
- [ ] Tài liệu selector đã được cập nhật vào `config/spider_config.py`

### 15.2 Tiêu chí DoD cho toàn bộ hệ thống Crawl

Hệ thống thu thập dữ liệu được coi là **HOÀN THÀNH** khi đáp ứng tất cả các điều kiện sau:

#### Dữ liệu

- [ ] **Trường ĐH:** ≥ 200 trường trong bảng `universities`, tỷ lệ đầy đủ thông tin ≥ 90%
- [ ] **Ngành học:** ≥ 500 ngành trong bảng `majors`, 100% có `holland_types`, ≥ 90% có `description`
- [ ] **Điểm chuẩn:** ≥ 10,000 bản ghi trong `admission_scores`, bao gồm dữ liệu 2020–2025
- [ ] **Thị trường lao động:** ≥ 50 nhóm nghề trong `job_categories` với đủ dữ liệu lương

#### Chất lượng

- [ ] Tỷ lệ bản ghi pass validation ≥ 95%
- [ ] Không có duplicate trên composite key
- [ ] Tỷ lệ ngành có `subject_combinations` đầy đủ ≥ 95%
- [ ] Admin đã review và approve Holland mapping qua UC20

#### Kỹ thuật

- [ ] Tất cả spiders có thể chạy lại mà không gây lỗi
- [ ] Scheduler tự động chạy đúng lịch trong 3 ngày liên tiếp
- [ ] API Admin (UC06) hoạt động đầy đủ (trigger, status, logs)
- [ ] Thời gian crawl toàn bộ < 4 giờ/lần
- [ ] Hệ thống tự phục hồi sau lỗi kết nối (retry logic hoạt động)

#### Tài liệu

- [ ] `docs/crawl/README.md` – index file cập nhật
- [ ] `docs/crawl/OPERATIONS.md` – hướng dẫn vận hành đã viết
- [ ] `craw-data/README.md` – hướng dẫn cài đặt và chạy

---

*← [07 – Rủi ro & Kiểm thử](./07_rui_ro_va_kiem_thu.md) | [09 – Phụ lục](./09_phu_luc.md) →*