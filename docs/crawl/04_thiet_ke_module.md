# 04 – Thiết kế Module Chi tiết

> 📂 Thuộc: [Kế hoạch Thu thập Dữ liệu – NLU-EduPath](./README.md)  
> ⬅️ Trước: [03 – Database Schema](./03_database_schema.md)  
> ➡️ Tiếp: [05 – Kế hoạch Sprint](./05_ke_hoach_sprint.md)

---

## Mục lục

- [7.1 Base Spider](#71-base-spider)
- [7.2 AdmissionScoreSpider](#72-admissionscorespider-ưu-tiên-1)
- [7.3 MajorInfoSpider](#73-majorinfospider-ưu-tiên-2)
- [7.4 JobMarketSpider](#74-jobmarketspider-ưu-tiên-3)
- [7.5 EnrichmentPipeline – Holland Mapping](#75-enrichmentpipeline--holland-mapping)

---

## 7.1 Base Spider

Mọi spider đều kế thừa `BaseSpider` để đảm bảo tính thống nhất và tránh lặp code:

```
BaseSpider
  ├── Tự động ghi crawl_log khi bắt đầu / kết thúc
  ├── Retry logic: tối đa 3 lần, delay tăng dần (exponential backoff)
  ├── Rate limiting: tuân thủ DOWNLOAD_DELAY trong config
  ├── User-Agent rotation: chọn ngẫu nhiên từ pool
  └── Error capturing: bắt exception, ghi log, không làm crash toàn bộ job
```

**Các thuộc tính bắt buộc khi kế thừa:**

| Thuộc tính | Kiểu | Mô tả |
|------------|------|-------|
| `name` | `str` | Tên spider, dùng để định danh trong `crawl_logs` |
| `allowed_domains` | `list[str]` | Danh sách domain được phép crawl |
| `start_urls` | `list[str]` | Danh sách URL khởi đầu |
| `custom_settings` | `dict` | Override cấu hình Scrapy cho spider cụ thể |

**Luồng lifecycle:**

```
__init__()
    │
    ▼
start_requests()          ← Sinh ra Request objects
    │
    ▼
parse()                   ← Xử lý response, yield Item hoặc Request mới
    │
    ▼
item_pipeline             ← Validate → Dedup → Normalize → Enrich → Store
    │
    ▼
closed()                  ← Cập nhật crawl_log: status, records_count
```

---

## 7.2 AdmissionScoreSpider (Ưu tiên #1)

**Mục tiêu:** Thu thập điểm chuẩn từ 2020–2025 cho toàn bộ trường ĐH.

**Nguồn chính:** `https://diemthi.tuyensinh247.com`

### Logic xử lý

```
1. Đọc danh sách trường từ DB (hoặc file seed nếu DB còn trống)
2. Với mỗi trường → sinh URL theo pattern:
   https://diemthi.tuyensinh247.com/diem-chuan/{university_code}/{year}.html
3. Parse bảng HTML: tên ngành | tổ hợp | điểm chuẩn | chỉ tiêu
4. Chuẩn hóa tên ngành → tra cứu major_code trong DB
5. Tạo AdmissionScoreItem và đưa vào pipeline
```

### CSS/XPath Selectors (tuyensinh247.com)

```
Table:     table.tb-diem-chuan
Row:       tbody > tr
Col[0]:    td:nth-child(1)  → major_name
Col[1]:    td:nth-child(2)  → subject_combination
Col[2]:    td:nth-child(3)  → cutoff_score
Col[3]:    td:nth-child(4)  → quota
```

> ⚠️ **Lưu ý:** Selectors cần xác minh lại khi bắt đầu code vì website có thể thay đổi cấu trúc HTML bất kỳ lúc nào. Tham khảo [Phụ lục B – Checklist Khảo sát Nguồn](./09_phu_luc.md#phụ-lục-b--checklist-khảo-sát-nguồn-dữ-liệu) trước khi code.

### Item Schema

```python
class AdmissionScoreItem:
    id:                 UUID   # Tự sinh
    university_id:      UUID   # FK → universities.id
    major_id:           UUID   # FK → majors.id
    year:               int
    admission_method:   str    # "THPT" | "Học bạ" | "ĐGNL"
    subject_combination: str   # "A00" | "A01" | ...
    cutoff_score:       float
    quota:              int | None
    note:               str | None
    scraped_at:         datetime
    source_url:         str
```

### Xử lý đặc biệt

- **Trường hợp nhiều phương thức xét tuyển:** Mỗi phương thức tạo một bản ghi riêng, phân biệt bởi trường `admission_method`.
- **Trường hợp điểm chuẩn dạng "Xét học bạ":** Lưu vào `admission_method = "Học bạ"`, ghi rõ trong `note`.
- **Trường hợp điểm cộng ưu tiên:** Ghi nguyên giá trị, thêm ghi chú `"Bao gồm điểm ưu tiên"` vào `note`.

---

## 7.3 MajorInfoSpider (Ưu tiên #2)

**Mục tiêu:** Thu thập thông tin mô tả ngành, tổ hợp môn xét tuyển, triển vọng nghề nghiệp.

**Nguồn:** Bộ GD&ĐT + các trang hướng nghiệp + Wikipedia tiếng Việt (làm phong phú mô tả)

### Logic xử lý

```
1. Đọc danh sách mã ngành chuẩn từ Bộ GD&ĐT (seed file JSON)
2. Với mỗi ngành → crawl trang mô tả ngành từ nguồn phù hợp
3. Parse: tên ngành, khối ngành, mô tả, ngành nghề sau tốt nghiệp
4. Đưa vào EnrichmentPipeline để tự động gán Holland types
5. Lưu vào DB với trạng thái is_published = FALSE
6. Admin review và approve qua UC20 trước khi AI sử dụng
```

### Item Schema

```python
class MajorInfoItem:
    id:                  UUID   # Tự sinh
    major_code:          str    # Mã ngành Bộ GD&ĐT, VD: "7480201"
    name:                str
    major_group:         str    # VD: "Kỹ thuật và Công nghệ"
    major_group_code:    str    # VD: "7480"
    description:         str
    career_options:      list[str]
    required_skills:     list[str]
    subject_combinations: list[str]
    study_duration:      int    # Năm
    degree_level:        str    # "bachelor" | "engineer"
    scraped_at:          datetime
    source_url:          str
```

### Chiến lược ghép nguồn

Vì không có một trang đơn lẻ nào chứa đầy đủ mọi thông tin, spider sẽ ghép từ nhiều nguồn:

| Trường dữ liệu | Nguồn chính |
|----------------|-------------|
| `major_code`, `name`, `major_group` | Bộ GD&ĐT (seed file) |
| `description` | Trang hướng nghiệp / Wikipedia |
| `career_options` | Trang tư vấn nghề nghiệp |
| `subject_combinations` | Đề án tuyển sinh các trường |
| `required_skills` | Tổng hợp từ tin tuyển dụng (TopCV) |

---

## 7.4 JobMarketSpider (Ưu tiên #3)

**Mục tiêu:** Thu thập dữ liệu lương và nhu cầu tuyển dụng theo nhóm nghề.

**Nguồn chính:** TopCV Salary Report + VietnamWorks

**Kỹ thuật:** Playwright (headless browser) — vì các trang này render bằng JavaScript.

### Logic xử lý

```
1. Playwright mở trình duyệt headless (Chromium)
2. Điều hướng đến trang thống kê lương theo ngành
3. Chờ element chính render (page.wait_for_selector)
4. Cuộn trang để lazy-load toàn bộ dữ liệu
5. Trích xuất: tên nhóm nghề, lương min/max, số tin tuyển dụng
6. Tổng hợp và tính median salary
7. Mapping nhóm nghề → major_code tương ứng
```

### Item Schema

```python
class JobCategoryItem:
    id:               UUID   # Tự sinh
    name:             str    # VD: "Kỹ sư Phần mềm"
    related_majors:   list[str]   # Danh sách major_code liên quan
    avg_salary_min:   int    # VNĐ/tháng
    avg_salary_max:   int
    median_salary:    int | None
    demand_level:     str    # "low" | "medium" | "high" | "very_high"
    growth_trend:     str    # "declining" | "stable" | "growing" | "booming"
    top_skills:       list[str]
    job_count_sample: int | None
    source:           str    # "topcv" | "vietnamworks"
    scraped_at:       datetime
```

### Xử lý Anti-bot

| Kỹ thuật | Cấu hình |
|----------|----------|
| User-Agent rotation | Pool 10+ UA thực tế từ Chrome/Firefox |
| Random delay | `random.uniform(2.0, 5.0)` giây giữa các request |
| Viewport giả | `1920x1080` (giống người dùng thật) |
| Disable webdriver flag | `navigator.webdriver = false` |
| Session cookies | Lưu và tái sử dụng session hợp lệ |

---

## 7.5 EnrichmentPipeline – Holland Mapping

Pipeline quan trọng nhất trong chuỗi xử lý, tự động gán nhãn **Holland RIASEC** cho từng ngành dựa trên từ khóa trong tên và mô tả ngành.

### Bảng mapping mặc định (keyword-based)

| Holland Type | Ký hiệu | Từ khóa trong tên/mô tả ngành |
|-------------|---------|-------------------------------|
| Realistic – "Do-er" | **R** | Kỹ thuật, Cơ khí, Điện, Điện tử, Xây dựng, Cơ điện, Hàng hải, Hàng không |
| Investigative – "Thinker" | **I** | Khoa học, Nghiên cứu, Công nghệ, Toán, Vật lý, Hóa học, Sinh học, Dữ liệu, AI |
| Artistic – "Creator" | **A** | Thiết kế, Mỹ thuật, Kiến trúc, Âm nhạc, Báo chí, Truyền thông, Điện ảnh, Ngôn ngữ |
| Social – "Helper" | **S** | Giáo dục, Y tế, Điều dưỡng, Xã hội, Tâm lý, Công tác xã hội, Du lịch, Khách sạn |
| Enterprising – "Persuader" | **E** | Kinh doanh, Quản trị, Marketing, Luật, Ngoại thương, Bất động sản, Tài chính ngân hàng |
| Conventional – "Organizer" | **C** | Kế toán, Kiểm toán, Thống kê, Hành chính, Thư viện, Lưu trữ, Bảo hiểm |

### Thuật toán gán nhãn

```
score = {R: 0, I: 0, A: 0, S: 0, E: 0, C: 0}

FOR mỗi từ khóa trong bảng mapping:
    IF từ khóa xuất hiện trong (major_name + description):
        score[holland_type] += weight

# Chọn tối đa 3 type có score cao nhất (> 0)
holland_types = top_3(score)
```

> **Lưu ý quan trọng:** Mapping tự động chỉ là bước **khởi tạo ban đầu**. Admin **bắt buộc phải review** và điều chỉnh kết quả qua giao diện **UC20 – Kiểm soát chất lượng dữ liệu** trước khi dữ liệu được AI Engine sử dụng. Kết quả chưa được approve sẽ có trạng thái `is_published = FALSE`.

### Trạng thái phê duyệt

```
[auto-mapped]
      │
      ▼
is_published = FALSE   ←── Chờ Admin review (UC20)
      │
      ├── Admin APPROVE ──► is_published = TRUE  ──► AI có thể dùng
      │
      └── Admin REJECT  ──► Admin sửa tay → APPROVE → is_published = TRUE
```

---

*Tài liệu này là một phần của bộ kế hoạch Thu thập Dữ liệu – NLU-EduPath 2025–2026.*