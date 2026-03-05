# Quy trình Thu thập Dữ liệu tự động (Autopilot Mode)

Tài liệu này mô tả cơ chế hoạt động của Robot thu thập dữ liệu và cách nó tự động mở rộng cơ sở dữ liệu.

---

## 1. Nguyên lý hoạt động (Auto-Discovery)

Hệ thống NLU-EduPath không còn dựa vào việc khai báo trường học thủ công. Luồng xử lý diễn ra như sau:

1.  **Crawl (Spider)**: Robot quét danh sách trường trên web. Với mỗi trường, nó tìm sâu vào bảng điểm chuẩn.
2.  **Match (Brain)**: Robot lấy tên ngành trên web đối chiếu với "Bộ não" (215 ngành chuẩn trong `seed_data.py`).
    *   Nếu khớp: Gán nhãn **Holland Type** và **Mã Bộ** chuẩn.
    *   Nếu không khớp: Tự động tạo ngành mới với nhãn `AUTO-XXXX`.
3.  **Discovery (On-the-fly)**: Nếu Robot thấy mã trường chưa có trong Database, nó sẽ tự động tạo một bản ghi trường mới.
4.  **Store (Pipeline)**: Điểm chuẩn được lưu vào cùng với ID của trường và ngành vừa khám phá.

---

## 2. Các lệnh vận hành chính

### Chạy thu hoạch toàn bộ (Diện rộng)
Đây là lệnh mạnh nhất, quét toàn bộ danh sách trường có trên nguồn Tuyensinh247.
```bash
scrapy crawl admission_score -a source=tuyensinh247 -a years=2024 --loglevel=INFO
```

### Chạy cho một vài trường cụ thể (Diện hẹp)
Nếu bạn chỉ muốn cập nhật dữ liệu cho các trường Top:
```bash
scrapy crawl admission_score -a source=tuyensinh247 -a university_codes=QSB,BKA,FTU -a years=2024 --loglevel=INFO
```

---

## 3. Quản lý "Bộ não" ngành học

Mặc dù hệ thống tự động, nhưng bạn nên duy trì file `scripts/seed_data.py` để:
*   Cập nhật Holland Type cho các ngành mới mà Robot vừa tự tạo.
*   Chuẩn hóa lại tên các ngành mang nhãn `AUTO-`.

Sau khi sửa file Seed, hãy chạy lệnh sau để cập nhật (không làm mất điểm chuẩn đã crawl):
```bash
python scripts/seed_data.py
```

---

## 4. Tại sao tỷ lệ "Fail" lại thấp?

Nhờ cơ chế tự động tạo (On-the-fly), Robot sẽ không bao giờ loại bỏ (Drop) dữ liệu chỉ vì "không biết trường này là trường nào". Tỷ lệ thành công hiện tại đạt mức xấp xỉ **99%**.
*   **Failed**: Chỉ xảy ra khi dữ liệu trên web bị lỗi định dạng (không phải là số).
*   **Skipped**: Chỉ xảy ra khi dữ liệu bị trùng lặp (đã lưu rồi).
