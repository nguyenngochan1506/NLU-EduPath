# Báo cáo Chất lượng Dữ liệu - Sprint 1 (Điểm chuẩn)

**Dự án:** NLU-EduPath  
**Ngày báo cáo:** 08/03/2026  
**Giai đoạn:** Sprint 1 - Thu thập Điểm chuẩn Đại học

---

## 1. Kết quả Tổng quan (Summary)

Dưới đây là thống kê thực tế từ Database sau đợt vận hành Robot thu thập dữ liệu (Autopilot Mode):

| Đối tượng                         | Số lượng bản ghi | Trạng thái         |
| :-------------------------------- | :--------------- | :----------------- |
| **Trường Đại học**                | 154              | ✅ Hoàn thành      |
| **Ngành học (Majors)**            | 605              | 🟡 Đang rà soát    |
| **Điểm chuẩn (Admission Scores)** | 4,713            | ✅ Đạt mục tiêu M1 |

---

## 2. Phân tích Chi tiết

### 2.1. Về Ngành học (Majors)

Hệ thống sử dụng cơ chế **Auto-Discovery** để phát hiện ngành học mới.

- **Ngành chuẩn (Seed):** 215 ngành (đã có Holland Type).
- **Ngành tự động phát hiện (Auto):** 388 ngành (mã `AUTO-XXXX`).
- **Tỷ lệ gán nhãn AI:** 35.5% đã có nhãn tính cách.
- **Kế hoạch:** Các ngành `AUTO-` sẽ được gán nhãn thủ công hoặc qua AI Enrichment ở Sprint 2.

### 2.2. Về Điểm chuẩn (Admission Scores)

Dữ liệu bao gồm các năm 2023, 2024 từ nguồn **Tuyensinh247**.

- **Phương thức xét tuyển:** Chủ yếu là THPT, Học bạ và ĐGNL.
- **Độ phủ:** Đã bao phủ hầu hết các trường Top đầu khu vực miền Nam và miền Bắc.

---

## 3. Nhật ký Vận hành (Crawl Logs)

Hệ thống đã trải qua 5 đợt chạy lớn:

- **Đợt thành công nhất:** +18,501 bản ghi (bao gồm cả dữ liệu thô chưa qua lọc trùng).
- **Lỗi phát sinh:** Một số trường hợp lỗi kết nối (Timeout) và lỗi định dạng điểm chuẩn trên web (đã được xử lý qua Validation Pipeline).
- **Tỷ lệ hợp lệ:** Ước tính đạt ~94% (Gần sát mục tiêu 95%).

---

## 4. Hành động Tiếp theo (Next Steps)

1.  **Chuẩn hóa Ngành học:** Gộp các ngành `AUTO-` bị trùng tên hoặc sai lệch mã bộ vào danh mục chuẩn.
2.  **Làm giàu dữ liệu:** Bắt đầu triển khai `MajorInfoSpider` để lấy mô tả ngành (Sprint 2).
3.  **Bổ sung Holland Type:** Sử dụng AI để gợi ý Holland Type cho 388 ngành mới phát hiện.

---

_Tài liệu này được tạo tự động dựa trên thực tế Database._
