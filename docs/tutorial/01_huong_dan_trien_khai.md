# Hướng dẫn Triển khai Hệ thống Autopilot (Sprint 0 & 1)

Tài liệu này hướng dẫn các bước thiết lập hệ thống NLU-EduPath ở chế độ **Tự động hoàn toàn (Autopilot)**.

---

## 1. Yêu cầu hệ thống
- **Python**: 3.12+
- **Docker & Docker Compose**: Để chạy PostgreSQL và Redis
- **Playwright**: Cần thiết để cào dữ liệu từ các trang web hiện đại (SPA).

---

## 2. Thiết lập hạ tầng & Môi trường

```bash
cd craw-data
# Khởi động Database & Redis
docker-compose up -d

# Cài đặt thư viện
pip install -r requirements.txt
playwright install chromium
```

---

## 3. Khởi tạo "Bộ não" Ngành học (Bắt buộc)

Trước khi cho Robot đi thu thập dữ liệu, bạn cần nạp danh mục ngành học chuẩn (215+ mã) để AI có thể tự động gán nhãn tính cách (Holland Type) cho dữ liệu sau này.

```bash
# Lệnh này sẽ xóa dữ liệu cũ và nạp lại từ điển ngành chuẩn
python scripts/seed_data.py --reset
```

---

## 4. Vận hành Robot Thu thập (Autopilot)

Bạn không cần khai báo danh sách trường. Chỉ cần ra lệnh cho Robot quét toàn bộ mạng lưới tuyển sinh. Logs sẽ hiển thị trực tiếp trong Terminal:

```bash
# Quét toàn bộ điểm chuẩn năm 2024 của tất cả các trường tại Việt Nam
scrapy crawl admission_score -a source=tuyensinh247 -a years=2024 --loglevel=INFO
```

**Các ký hiệu cần chú ý trong Log:**
- `🚀 [START]`: Phát hiện danh sách hàng trăm trường.
- `🔍 [PROCESS]`: Robot đang truy cập sâu vào một trường cụ thể.
- `🆕 [NEW SCHOOL]`: Robot phát hiện và tự tạo một trường đại học mới trong DB.
- `🎯 [NEW MAJOR]`: Robot phát hiện và tự tạo một ngành học mới chưa có trong từ điển.
- `✅ [DONE]`: Robot đã thu thập xong dữ liệu của một trường.

---

## 5. Script Triển khai Nhanh (Khuyên dùng)

Để đơn giản hóa, bạn có thể sử dụng script `init_and_crawl.sh` ngay tại thư mục gốc của dự án. Script này sẽ tự động:
1. Kích hoạt môi trường ảo (`venv`).
2. Nạp/Cập nhật danh mục ngành học chuẩn (`seed_data.py`).
3. Khởi động Robot cào dữ liệu từ Tuyensinh247 cho tất cả các năm.

```bash
# Cấp quyền thực thi (chỉ cần làm 1 lần)
chmod +x init_and_crawl.sh

# Chạy toàn bộ tiến trình
./init_and_crawl.sh
```

Nếu muốn giới hạn phạm vi cào (ví dụ chỉ cào trường Đại học Nông Lâm - NLS), bạn có thể thêm tham số:
```bash
./init_and_crawl.sh -a university_codes=NLS
```

---

## 6. Lưu ý Quan trọng (Cần đọc kỹ)

### 6.1 Luôn sử dụng Môi trường ảo (Virtual Environment)
Nếu bạn gặp lỗi `ModuleNotFoundError: No module named 'sqlalchemy'` hoặc các thư viện khác, đó là do bạn đang dùng Python của hệ thống.

**Giải pháp (Chọn 1 trong 2):**
*   **Cách A (Khuyên dùng)**: Kích hoạt môi trường ảo trước khi chạy:
    ```bash
    source venv/bin/activate
    python scripts/seed_data.py --reset
    ```
*   **Cách B**: Sử dụng đường dẫn trực tiếp đến venv:
    ```bash
    ./venv/bin/python scripts/seed_data.py --reset
    ./venv/bin/scrapy crawl admission_score ...
    ```

### 6.2 Thư mục làm việc (Working Directory)
Mọi lệnh lệnh Python, Scrapy, Alembic **PHẢI** được thực thi khi bạn đang đứng ở thư mục `craw-data/`.
*   ✅ Đúng: `ngochandev/craw-data $ python scripts/seed_data.py`
*   ❌ Sai: `ngochandev/ $ python craw-data/scripts/seed_data.py`

### 6.3 Trạng thái Database
Đảm bảo các container Docker đang chạy trước khi thực hiện bất kỳ lệnh nào liên quan đến dữ liệu:
```bash
docker ps
# Nếu không thấy container nào, hãy chạy: docker-compose up -d
```
