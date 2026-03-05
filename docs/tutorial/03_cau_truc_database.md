# Cấu trúc Cơ sở dữ liệu (Database Schema)

Tài liệu này mô tả chi tiết các bảng và ý nghĩa từng trường dữ liệu trong hệ thống NLU-EduPath.

---

## 1. Bảng `universities` (Trường Đại học)
Lưu trữ thông tin định danh và hồ sơ của các cơ sở giáo dục đại học.

| Trường (Field) | Kiểu dữ liệu | Ý nghĩa |
| :--- | :--- | :--- |
| `id` | UUID | Khóa chính (Primary Key) |
| `university_code` | String(20) | Mã trường (VD: QSB, BKA, NLU) - **Unique** |
| `name` | String(255) | Tên đầy đủ của trường |
| `short_name` | String(50) | Tên viết tắt (VD: HCMUT, HUST) |
| `university_type` | String(50) | Loại hình: `public` (Công lập), `private` (Dân lập) |
| `region` | String(50) | Khu vực: `north`, `central`, `south` |
| `province` | String(100) | Tỉnh/Thành phố trụ sở |
| `address` | Text | Địa chỉ chi tiết |
| `website` | String(255) | Website chính thức của trường |
| `admission_url` | String(255) | Trang tin tuyển sinh của trường |
| `tuition_min` | BigInt | Học phí tối thiểu ước tính (VNĐ/năm) |
| `tuition_max` | BigInt | Học phí tối đa ước tính (VNĐ/năm) |
| `is_active` | Boolean | Trạng thái hoạt động (Default: True) |
| `scraped_at` | DateTime | Thời điểm thu thập dữ liệu gần nhất |

---

## 2. Bảng `majors` (Danh mục Ngành học)
Đây là "Bộ não" của hệ thống, nơi lưu trữ định nghĩa các ngành học chuẩn.

| Trường (Field) | Kiểu dữ liệu | Ý nghĩa |
| :--- | :--- | :--- |
| `id` | UUID | Khóa chính |
| `major_code` | String(20) | Mã ngành chuẩn (7 chữ số) hoặc mã `AUTO-` |
| `name` | String(255) | Tên ngành học chuẩn |
| `major_group` | String(255) | Nhóm ngành (VD: Máy tính và CNTT) |
| `major_group_code` | String(10) | 3 chữ số đầu của mã ngành |
| `description` | Text | Mô tả ngắn gọn về ngành học |
| `holland_types` | JSONB (Array) | **Nhãn tính cách**: List các nhóm R, I, A, S, E, C |
| `study_duration` | Float | Thời gian đào tạo tiêu chuẩn (năm) |
| `degree_level` | String(50) | Trình độ: `bachelor`, `engineer`, `master` |
| `career_options` | JSONB (Array) | **Các vị trí việc làm** sau khi tốt nghiệp |
| `required_skills` | JSONB (Array) | **Kỹ năng cần thiết** (VD: Logic, Ngoại ngữ) |
| `subject_combinations`| JSONB (Array) | Các tổ hợp môn thường dùng (VD: A00, D01) |
| `career_anchor_tags` | JSONB (Array) | Neo nghề nghiệp (Sử dụng cho AI tư vấn sâu) |

> **Lưu ý**: Các trường `career_options`, `required_skills`, `career_anchor_tags` hiện đang để trống cho các ngành tự động khám phá. Dữ liệu này sẽ được lấp đầy ở **Sprint 2** thông qua AI hoặc Seed Data cập nhật.

---

## 3. Bảng `admission_scores` (Điểm chuẩn)
Lưu trữ dữ liệu lịch sử điểm chuẩn qua các năm.

| Trường (Field) | Kiểu dữ liệu | Ý nghĩa |
| :--- | :--- | :--- |
| `id` | UUID | Khóa chính |
| `university_id` | UUID | Khóa ngoại liên kết bảng `universities` |
| `major_id` | UUID | Khóa ngoại liên kết bảng `majors` |
| `year` | SmallInt | Năm tuyển sinh (VD: 2024) |
| `admission_method` | String(100) | Phương thức: `THPT`, `hoc_ba`, `DGNL` |
| `subject_combination`| String(10) | Tổ hợp môn xét tuyển (VD: A01, B00) |
| `cutoff_score` | Numeric(5,2) | **Điểm chuẩn** (Thang 30 hoặc 100) |
| `quota` | BigInt | Chỉ tiêu tuyển sinh của ngành đó |
| `note` | Text | Ghi chú thêm (VD: Tiêu chí phụ) |
| `source_url` | String(500) | Link nguồn trang web lấy dữ liệu |

---

## 4. Bảng `crawl_logs` (Nhật ký thu thập)
Theo dõi "sức khỏe" và hiệu suất của các đợt chạy Robot.

| Trường (Field) | Kiểu dữ liệu | Ý nghĩa |
| :--- | :--- | :--- |
| `id` | UUID | Khóa chính |
| `spider_name` | String(100) | Tên spider (VD: `admission_score`) |
| `status` | String(20) | Trạng thái: `success`, `failed`, `running` |
| `records_new` | Integer | Số bản ghi mới được thêm |
| `records_updated` | Integer | Số bản ghi được cập nhật |
| `records_failed` | Integer | Số bản ghi bị lỗi kỹ thuật |
| `records_skipped` | Integer | Số bản ghi bị trùng hoặc bỏ qua |
| `error_summary` | Text | Tóm tắt lỗi nếu có |
| `started_at` | DateTime | Thời điểm Robot bắt đầu chạy |
| `finished_at` | DateTime | Thời điểm Robot kết thúc |
