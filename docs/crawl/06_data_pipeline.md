# 06 – Data Pipeline: Làm sạch, Lập lịch & Giám sát

> **Thuộc về:** Kế hoạch Thu thập Dữ liệu – NLU-EduPath  
> **Liên quan:** [03_database_schema.md](./03_database_schema.md) · [04_thiet_ke_module.md](./04_thiet_ke_module.md)  
> **Điều hướng:** [← Sprint Plan](./05_ke_hoach_sprint.md) · [Rủi ro & Kiểm thử →](./07_rui_ro_va_kiem_thu.md)

---

## Mục lục

- [9. Quy trình Làm sạch & Chuẩn hóa Dữ liệu](#9-quy-trình-làm-sạch--chuẩn-hóa-dữ-liệu)
- [10. Lập lịch & Tự động hóa](#10-lập-lịch--tự-động-hóa)
- [11. Giám sát & Logging](#11-giám-sát--logging)

---

## 9. Quy trình Làm sạch & Chuẩn hóa Dữ liệu

Dữ liệu thô từ nhiều nguồn web luôn có sự không nhất quán. Pipeline làm sạch được thiết kế để tự động hóa tối đa, chỉ đẩy lên Admin những gì thực sự cần review thủ công.

### 9.1 Chuẩn hóa tên trường

**Vấn đề:** Cùng một trường xuất hiện với nhiều tên khác nhau trên các nguồn:

```
"Đại học Bách Khoa Hà Nội"
"Trường ĐH Bách khoa Hà Nội"
"ĐH Bách Khoa - HN"
"Hanoi University of Science and Technology"
```

**Giải pháp:** Dùng `university_code` (mã Bộ GD&ĐT) làm khóa định danh duy nhất. Bảng alias sẽ map các tên biến thể về cùng một `university_code`.

```
Tên thô từ web  ──►  Bảng alias lookup  ──►  university_code  ──►  universities.id (UUID)
```

> Nếu tên không khớp bất kỳ alias nào → ghi vào hàng đợi `pending_review` để Admin xử lý thủ công.

---

### 9.2 Chuẩn hóa tổ hợp môn

**Mapping chuẩn** (theo quy định Bộ GD&ĐT):

| Tên thường gặp trên web | Mã chuẩn |
|-------------------------|----------|
| Toán – Lý – Hóa | `A00` |
| Toán – Lý – Anh | `A01` |
| Toán – Hóa – Sinh | `B00` |
| Văn – Sử – Địa | `C00` |
| Toán – Văn – Anh | `D01` |
| Toán – Anh – Tin | `X26` |
| Toán – Lý – Tin | `X06` |

> Mọi biến thể chính tả (viết thường, có dấu gạch ngang, viết tắt...) đều được map về mã chuẩn trong bước `NormalizationPipeline`.

---

### 9.3 Chuẩn hóa điểm chuẩn

| Quy tắc | Chi tiết |
|---------|----------|
| Thang điểm | Chuyển mọi điểm về **thang 30** (3 môn × 10 điểm) |
| Điểm học bạ | Ghi chú riêng `admission_method = "hoc_ba"`, không trộn với điểm THPT |
| Loại bỏ bất hợp lệ | `cutoff_score < 10.0` hoặc `> 30.0` → fail validation, ghi error log |
| Điểm ưu tiên | Lưu điểm gốc, ghi chú loại ưu tiên vào trường `note` |

---

### 9.4 Validation Rules

Mọi item đều phải qua kiểm tra validation trước khi vào pipeline tiếp theo. Item fail sẽ bị loại, ghi log lỗi chi tiết.

| Mã rule | Đối tượng | Điều kiện |
|---------|-----------|-----------|
| `V01` | `university_code` | Match regex `[A-Z0-9]{2,10}` |
| `V02` | `cutoff_score` | Trong khoảng `[10.0, 30.0]` |
| `V03` | `year` | Trong khoảng `[2018, năm hiện tại + 1]` |
| `V04` | `subject_combination` | Phải nằm trong danh sách mã chuẩn cho phép |
| `V05` | `major_code` | Match regex `[0-9]{7}` |
| `V06` | Tất cả trường `NOT NULL` | Không được để `NULL` hoặc chuỗi rỗng |
| `V07` | Mọi trường URL | Phải bắt đầu bằng `http://` hoặc `https://` |

---

## 10. Lập lịch & Tự động hóa

### 10.1 Lịch chạy tự động

| Spider | Tần suất | Giờ chạy | Lý do |
|--------|----------|----------|-------|
| `AdmissionScoreSpider` | Hàng ngày | `02:00` | Điểm chuẩn cập nhật liên tục theo mùa tuyển sinh |
| `UniversitySpider` | Hàng tuần | Chủ nhật `01:00` | Thông tin trường ít thay đổi |
| `MajorInfoSpider` | Hàng tuần | Thứ Hai `01:00` | Thông tin ngành tương đối ổn định |
| `JobMarketSpider` | 2 lần/tuần | Thứ Ba & Sáu `03:00` | Thị trường lao động biến động nhanh hơn |

---

### 10.2 Cơ chế Retry (Exponential Backoff)

```
Lần 1 thất bại  ──►  chờ  5 phút  ──►  thử lại
Lần 2 thất bại  ──►  chờ 15 phút  ──►  thử lại
Lần 3 thất bại  ──►  ghi log CRITICAL + gửi cảnh báo Admin
                ──►  đánh dấu task FAILED, dừng retry tự động
```

> Admin có thể trigger lại thủ công qua API hoặc Dashboard sau khi xác nhận nguyên nhân lỗi.

---

### 10.3 API Endpoints cho Admin (UC06)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/admin/crawl/sources` | Danh sách nguồn dữ liệu và trạng thái hiện tại |
| `POST` | `/api/admin/crawl/trigger` | Kích hoạt crawl thủ công cho một spider cụ thể |
| `GET` | `/api/admin/crawl/status/{job_id}` | Trạng thái của một job đang chạy |
| `GET` | `/api/admin/crawl/logs` | Lịch sử tất cả các lần crawl (phân trang) |
| `PUT` | `/api/admin/crawl/schedule` | Cập nhật lịch chạy tự động |
| `DELETE` | `/api/admin/crawl/cancel/{job_id}` | Hủy một job đang chạy |

**Request body mẫu cho `POST /trigger`:**

```json
{
  "spider_name": "admission_score_spider",
  "mode": "manual",
  "options": {
    "year_from": 2023,
    "year_to": 2025,
    "university_codes": ["QSB", "QSE", "BKA"]
  }
}
```

---

## 11. Giám sát & Logging

### 11.1 Cấu trúc Log

Mỗi lần chạy spider ghi một bản ghi vào bảng `crawl_logs`. Cấu trúc JSON tương ứng:

```json
{
  "id": "018f4c2e-7a3b-7d1e-9c4f-2b8e1a0d5f3c",
  "spider_name": "admission_score_spider",
  "status": "success",
  "started_at": "2025-06-01T02:00:00Z",
  "finished_at": "2025-06-01T02:14:23Z",
  "records_new": 156,
  "records_updated": 23,
  "records_failed": 2,
  "error_summary": "2 records failed V02: cutoff_score out of range [10,30]",
  "triggered_by": "scheduler"
}
```

> `id` là **UUID v7** – đảm bảo sắp xếp theo thời gian tự nhiên, thuận tiện cho phân trang log.

---

### 11.2 Cảnh báo tự động

| Điều kiện | Mức độ | Hành động tự động |
|-----------|--------|-------------------|
| Spider thất bại 3 lần liên tiếp | 🔴 CRITICAL | Gửi thông báo Zalo/email cho Admin |
| `records_failed` > 10% tổng bản ghi | 🟡 WARNING | Ghi log, hiển thị banner cảnh báo trên Dashboard |
| Crawl chạy quá 2 giờ mà chưa kết thúc | 🟡 WARNING | Tự động kill process và tạo retry job |
| Dung lượng DB vượt 80% | 🔴 CRITICAL | Cảnh báo ngay, không chờ lần crawl tiếp theo |

---

### 11.3 Dashboard Metrics (UC06 – Admin)

Giao diện Dashboard hiển thị tóm tắt trạng thái hệ thống crawl:

```
┌─────────────────────────────────────────────────────────────┐
│                  CRAWL SYSTEM DASHBOARD                     │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Last Run     │ Status       │ New Records  │ Failed        │
│ 2 giờ trước  │ ✅ Success   │ 156          │ 2             │
├──────────────┴──────────────┴──────────────┴───────────────┤
│ Tổng dữ liệu hiện có trong DB                               │
│   🏫 Trường ĐH   :   214 trường                             │
│   📚 Ngành học   :   523 ngành                              │
│   📊 Điểm chuẩn  : 12,450 bản ghi  (2020 – 2025)           │
│   💼 Nhóm nghề   :    57 nhóm                               │
├─────────────────────────────────────────────────────────────┤
│ ⏰ Lịch chạy tiếp theo                                      │
│   Hôm nay 02:00  →  admission_score_spider                  │
│   Thứ Hai 01:00  →  major_info_spider                       │
└─────────────────────────────────────────────────────────────┘
```

---

*← [05 – Kế hoạch Sprint](./05_ke_hoach_sprint.md) · [07 – Rủi ro & Kiểm thử →](./07_rui_ro_va_kiem_thu.md)*