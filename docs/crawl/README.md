# 📦 Tài liệu Thu thập Dữ liệu – NLU-EduPath

**Use Case liên quan:** UC06 – Cấu hình & Kích hoạt Web Scraping  
**Mức độ ưu tiên:** 🔴 Rất Cao (Critical)  
**Phiên bản:** v1.0 | **Năm:** 2025

> Không có dữ liệu → AI không thể hoạt động. Đây là module nền tảng của toàn bộ hệ thống.

---

## 📂 Cấu trúc tài liệu

| File | Nội dung | Đọc khi nào |
|------|----------|-------------|
| **`01_tong_quan_va_du_lieu.md`** | Mục tiêu, bản đồ dữ liệu, danh sách nguồn web | Đọc đầu tiên – hiểu bức tranh tổng thể |
| **`02_kien_truc_va_cong_nghe.md`** | Sơ đồ kiến trúc, data flow, tech stack, cấu trúc thư mục | Trước khi setup môi trường |
| **`03_database_schema.md`** | ERD, SQL schema đầy đủ (UUID), index | Trước khi viết migration |
| **`04_thiet_ke_module.md`** | Chi tiết từng Spider, Pipeline, Holland mapping | Khi bắt đầu code từng module |
| **`05_ke_hoach_sprint.md`** | Sprint 0–5, task list, output từng sprint | Theo dõi tiến độ hàng tuần |
| **`06_data_pipeline.md`** | Làm sạch dữ liệu, lịch chạy tự động, API Admin, logging | Khi implement pipeline & scheduler |
| **`07_rui_ro_va_kiem_thu.md`** | Bảng rủi ro, unit test, integration test, data quality | Trước khi deploy |
| **`08_timeline_va_dod.md`** | Timeline 6 tuần, phân công, milestone, Definition of Done | Review tiến độ với giảng viên |
| **`09_phu_luc.md`** | Seed data 50 trường, checklist khảo sát nguồn | Khi chuẩn bị seed data |

---

## 🚀 Thứ tự đọc đề xuất

```
Lần đầu tiếp cận:
  01 → 02 → 03 → 05

Khi bắt đầu code:
  04 → 06 → 09

Trước khi nộp báo cáo:
  07 → 08
```

---

## ⚡ Tóm tắt nhanh

- **Ngôn ngữ:** Python 3.11+
- **Framework:** Scrapy (static) + Playwright (dynamic JS)
- **Queue:** Celery + Redis
- **Database:** PostgreSQL 15+ (UUID primary keys)
- **Thời gian triển khai:** ~6 tuần
- **Dữ liệu mục tiêu:** 200+ trường ĐH · 500+ ngành học · Điểm chuẩn 2020–2025 · 50+ nhóm nghề

---

*Cập nhật lần cuối: 2025 – NLU-EduPath Team*