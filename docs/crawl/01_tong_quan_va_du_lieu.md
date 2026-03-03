# 01 – Tổng quan, Dữ liệu & Nguồn thu thập

**Dự án:** NLU-EduPath – Hệ thống Hướng nghiệp & Gợi ý Ngành học  
**Phiên bản:** v1.0 | **Cập nhật:** 2025  
**Use Case liên quan:** UC06 – Cấu hình & Kích hoạt Web Scraping  
**Mức độ ưu tiên:** 🔴 Rất Cao (Critical) – Không có dữ liệu, AI không thể hoạt động

---

## Điều hướng tài liệu

| File | Nội dung |
|------|----------|
| **01\_tong\_quan\_va\_du\_lieu.md** | ← Bạn đang ở đây |
| [02\_kien\_truc\_va\_cong\_nghe.md](./02_kien_truc_va_cong_nghe.md) | Kiến trúc hệ thống & Tech Stack |
| [03\_database\_schema.md](./03_database_schema.md) | Thiết kế Database Schema (UUID) |
| [04\_thiet\_ke\_module.md](./04_thiet_ke_module.md) | Thiết kế Module & Spider |
| [05\_ke\_hoach\_sprint.md](./05_ke_hoach_sprint.md) | Kế hoạch triển khai từng Sprint |
| [06\_data\_pipeline.md](./06_data_pipeline.md) | Data Pipeline, Lập lịch & Giám sát |
| [07\_rui\_ro\_va\_kiem\_thu.md](./07_rui_ro_va_kiem_thu.md) | Quản lý Rủi ro & Kế hoạch Test |
| [08\_timeline\_va\_dod.md](./08_timeline_va_dod.md) | Timeline, Phân công & DoD |
| [09\_phu\_luc.md](./09_phu_luc.md) | Phụ lục: Seed Data & Checklist |

---

## 1. Tổng quan & Mục tiêu

### 1.1 Bối cảnh

NLU-EduPath là hệ thống gợi ý hướng nghiệp cho học sinh THPT, sử dụng thuật toán **Content-Based Filtering** kết hợp với kết quả trắc nghiệm tâm lý **Holland RIASEC** và **Career Anchors** để đề xuất ngành học phù hợp.

Toàn bộ engine AI phụ thuộc vào chất lượng và độ phủ của dữ liệu tuyển sinh, thông tin ngành học và thị trường lao động được thu thập tự động từ web.

### 1.2 Vai trò trong hệ thống

```
[Nguồn Web] ──► [Web Crawler] ──► [Data Pipeline] ──► [Database]
                                                           │
                                               ┌───────────┼───────────┐
                                               ▼           ▼           ▼
                                         [AI Engine]  [Student UI] [Admin UI]
```

### 1.3 Mục tiêu cụ thể

| # | Mục tiêu | Chỉ số đo lường |
|---|----------|-----------------|
| 1 | Thu thập thông tin tuyển sinh ≥ 200 trường ĐH | Số trường trong DB |
| 2 | Thu thập điểm chuẩn lịch sử từ 2020–2025 | Số bản ghi điểm chuẩn |
| 3 | Thu thập ≥ 500 ngành học với đầy đủ thông tin | Số ngành trong DB |
| 4 | Thu thập dữ liệu thị trường lao động ≥ 50 nhóm nghề | Số nhóm nghề có dữ liệu lương |
| 5 | Tỷ lệ dữ liệu hợp lệ sau làm sạch ≥ 95% | Tỷ lệ pass validation |
| 6 | Thời gian làm mới dữ liệu tự động hàng ngày | Uptime scheduler |

---

## 2. Dữ liệu cần thu thập

### 2.1 Bản đồ dữ liệu tổng thể

```
DỮ LIỆU CẦN THU THẬP
├── 🏫 Thông tin Trường Đại học
│   ├── Thông tin cơ bản (tên, mã, địa chỉ, loại hình)
│   ├── Thông tin tuyển sinh (chỉ tiêu, học phí, phương thức xét tuyển)
│   └── Tổ hợp môn xét tuyển theo ngành
│
├── 📚 Thông tin Ngành học
│   ├── Tên ngành, mã ngành (theo chuẩn Bộ GD&ĐT)
│   ├── Mô tả ngành, chương trình đào tạo
│   ├── Kỹ năng yêu cầu, triển vọng nghề nghiệp
│   └── Mapping Holland RIASEC + Career Anchors
│
├── 📊 Điểm chuẩn lịch sử (2020–2025)
│   ├── Điểm chuẩn theo năm, theo trường, theo ngành
│   ├── Điểm theo từng tổ hợp môn (A00, A01, B00, D01...)
│   └── Phương thức xét tuyển (THPT, Đánh giá năng lực, Học bạ...)
│
└── 💼 Thị trường lao động
    ├── Nhu cầu tuyển dụng theo ngành nghề
    ├── Mức lương trung bình / median theo ngành
    ├── Kỹ năng được yêu cầu nhiều nhất
    └── Xu hướng tăng trưởng việc làm
```

### 2.2 Chi tiết từng loại dữ liệu

> **Lưu ý về ID:** Tất cả các trường `id` trong hệ thống đều dùng **UUID v4** được sinh tự động (`gen_random_uuid()`), không dùng SERIAL/integer. Xem chi tiết schema tại [03\_database\_schema.md](./03_database_schema.md).

#### A. Thông tin Trường Đại học

| Trường | Kiểu dữ liệu | Bắt buộc | Mô tả |
|--------|-------------|----------|-------|
| `id` | UUID | ✅ | Khóa chính, sinh tự động |
| `university_code` | String | ✅ | Mã do Bộ GD&ĐT cấp (VD: QSX, BKA...) |
| `name` | String | ✅ | Tên đầy đủ |
| `short_name` | String | ✅ | Tên viết tắt (VD: UEH, NEU, HUST) |
| `type` | Enum | ✅ | `public` / `private` / `foreign_affiliated` |
| `region` | Enum | ✅ | `north` / `central` / `south` |
| `province` | String | ✅ | Tỉnh/thành phố |
| `address` | String | ⬜ | Địa chỉ chi tiết |
| `website` | String | ✅ | URL trang chủ |
| `admission_url` | String | ✅ | URL trang tuyển sinh |
| `logo_url` | String | ⬜ | URL logo trường |
| `tuition_min` | Number | ⬜ | Học phí thấp nhất (VNĐ/năm) |
| `tuition_max` | Number | ⬜ | Học phí cao nhất (VNĐ/năm) |
| `established_year` | Number | ⬜ | Năm thành lập |
| `scraped_at` | DateTime | ✅ | Thời điểm thu thập |
| `source_url` | String | ✅ | URL nguồn |

#### B. Thông tin Ngành học

| Trường | Kiểu dữ liệu | Bắt buộc | Mô tả |
|--------|-------------|----------|-------|
| `id` | UUID | ✅ | Khóa chính, sinh tự động |
| `major_code` | String | ✅ | Mã ngành theo Bộ GD&ĐT (VD: 7480201) |
| `name` | String | ✅ | Tên ngành |
| `major_group` | String | ✅ | Khối ngành (VD: Kỹ thuật, Kinh tế, Y dược...) |
| `description` | String | ✅ | Mô tả ngành học |
| `career_options` | Array | ✅ | Danh sách nghề nghiệp có thể làm |
| `required_skills` | Array | ✅ | Kỹ năng cần có |
| `subject_combinations` | Array | ✅ | Các tổ hợp môn xét tuyển |
| `holland_types` | Array | ✅ | Mapping Holland RIASEC (R/I/A/S/E/C) |
| `career_anchors` | Array | ✅ | Mapping Career Anchors |
| `study_duration` | Number | ⬜ | Thời gian đào tạo (năm) |
| `degree_level` | Enum | ✅ | `bachelor` / `engineer` / `master` |

#### C. Điểm chuẩn lịch sử

| Trường | Kiểu dữ liệu | Bắt buộc | Mô tả |
|--------|-------------|----------|-------|
| `id` | UUID | ✅ | Khóa chính, sinh tự động |
| `university_id` | UUID | ✅ | FK → universities.id |
| `major_id` | UUID | ✅ | FK → majors.id |
| `year` | Number | ✅ | Năm tuyển sinh |
| `admission_method` | String | ✅ | Phương thức xét tuyển |
| `subject_combination` | String | ✅ | Tổ hợp môn (VD: A00, A01) |
| `cutoff_score` | Float | ✅ | Điểm chuẩn |
| `quota` | Number | ⬜ | Chỉ tiêu |
| `note` | String | ⬜ | Ghi chú đặc biệt |
| `scraped_at` | DateTime | ✅ | Thời điểm thu thập |
| `source_url` | String | ✅ | URL nguồn |

#### D. Dữ liệu thị trường lao động

| Trường | Kiểu dữ liệu | Bắt buộc | Mô tả |
|--------|-------------|----------|-------|
| `id` | UUID | ✅ | Khóa chính, sinh tự động |
| `name` | String | ✅ | Tên nhóm nghề |
| `related_majors` | Array | ✅ | Danh sách UUID các ngành liên quan |
| `avg_salary_min` | Number | ✅ | Lương trung bình thấp nhất (VNĐ/tháng) |
| `avg_salary_max` | Number | ✅ | Lương trung bình cao nhất (VNĐ/tháng) |
| `median_salary` | Number | ⬜ | Lương trung vị |
| `demand_level` | Enum | ✅ | `low` / `medium` / `high` / `very_high` |
| `growth_trend` | Enum | ✅ | `declining` / `stable` / `growing` / `booming` |
| `top_skills` | Array | ✅ | Kỹ năng phổ biến nhất |
| `job_count_sample` | Number | ⬜ | Số tin tuyển dụng mẫu |
| `scraped_at` | DateTime | ✅ | Thời điểm thu thập |
| `source` | String | ✅ | Nguồn dữ liệu |

---

## 3. Nguồn dữ liệu mục tiêu

### 3.1 Danh sách nguồn chính

| # | Tên nguồn | URL | Loại dữ liệu | Ưu tiên | Ghi chú |
|---|-----------|-----|-------------|---------|---------|
| 1 | Cổng thông tin tuyển sinh Bộ GD&ĐT | `https://tuyensinh.moet.gov.vn` | Thông tin chính thức tuyển sinh | 🔴 Cao | Nguồn chính thống |
| 2 | Tuyensinh247 | `https://tuyensinh247.com` | Điểm chuẩn, ngành học, trường ĐH | 🔴 Cao | Dữ liệu tổng hợp đầy đủ |
| 3 | Điểm thi Tuyensinh247 | `https://diemthi.tuyensinh247.com` | Điểm chuẩn lịch sử | 🔴 Cao | Nhiều năm, dễ parse |
| 4 | Tuyensinh.vn | `https://tuyensinh.vn` | Thông tin trường, ngành, điểm chuẩn | 🟡 Trung bình | Backup source |
| 5 | Website từng trường ĐH | Từng website trường | Đề án tuyển sinh chính thức | 🔴 Cao | Cần spider đa trang |
| 6 | TopCV | `https://topcv.vn` | Thị trường lao động, lương | 🟡 Trung bình | Cần xử lý anti-bot |
| 7 | VietnamWorks | `https://vietnamworks.com` | Nhu cầu tuyển dụng, lương | 🟡 Trung bình | Có API không chính thức |
| 8 | CareerBuilder Vietnam | `https://careerbuilder.vn` | Lương theo ngành | 🟢 Thấp | Backup lao động |
| 9 | Tra cứu mã ngành Bộ GD&ĐT | `https://qlgd.moet.gov.vn` | Mã ngành chuẩn, nhóm ngành | 🔴 Cao | Chuẩn hóa mã ngành |
| 10 | Hướng nghiệp 4.0 | Các trang tư vấn hướng nghiệp | Mô tả nghề nghiệp | 🟢 Thấp | Bổ sung mô tả |

### 3.2 Chiến lược tiếp cận từng nguồn

#### Nguồn 1–3 & 9: Bộ GD&ĐT & Tuyensinh247

- **Phương pháp:** Scrapy Spider + BeautifulSoup
- **Robots.txt:** Kiểm tra và tuân thủ trước khi crawl
- **Rate limiting:** 2–3 requests/giây
- **Dữ liệu trọng tâm:** Điểm chuẩn 2020–2025, mã ngành chuẩn

#### Nguồn 5: Website từng trường ĐH

- **Phương pháp:** Scrapy CrawlSpider với link following
- **Danh sách seed:** ~50 trường lớn trước, mở rộng sau
- **Ưu tiên:** Các trường tại TP.HCM, Hà Nội, Đà Nẵng

#### Nguồn 6–8: Thị trường lao động

- **Phương pháp:** Playwright (headless browser) do trang render bằng JavaScript
- **Dữ liệu cần:** Tên nghề, mức lương, kỹ năng yêu cầu, số lượng tin tuyển dụng
- **Anti-bot:** Rotate User-Agent, random delay, session cookies

---

*Tiếp theo: [02\_kien\_truc\_va\_cong\_nghe.md](./02_kien_truc_va_cong_nghe.md)*