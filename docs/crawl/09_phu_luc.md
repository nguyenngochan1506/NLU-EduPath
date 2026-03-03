# Phụ lục – Dữ liệu Tham khảo & Checklist

**Thuộc về:** Kế hoạch Thu thập Dữ liệu – NLU-EduPath  
**Cập nhật lần cuối:** 2025

---

## Phụ lục A – Seed Data: Danh sách 50 trường ưu tiên

> Đây là danh sách các trường được crawl **đầu tiên** trong Sprint 1 & Sprint 3.  
> Ưu tiên theo mức độ phổ biến, số ngành đào tạo và phân bố địa lý.

### Khu vực TP.HCM & Miền Nam

| STT | Tên trường | Mã trường | Tên viết tắt | Ghi chú |
|-----|-----------|-----------|-------------|---------|
| 1 | ĐH Quốc gia TP.HCM | QSX | ĐHQG-HCM | Hệ thống đại học |
| 2 | ĐH Bách khoa TP.HCM | QSB | HCMUT | Kỹ thuật – Công nghệ |
| 3 | ĐH Kinh tế TP.HCM | QSE | UEH | Kinh tế – Quản trị |
| 4 | ĐH Sư phạm Kỹ thuật TP.HCM | QST | HCMUTE | Kỹ thuật – Sư phạm |
| 5 | ĐH Khoa học Tự nhiên TP.HCM | QSN | HCMUS | Khoa học cơ bản |
| 6 | ĐH Khoa học Xã hội & Nhân văn TP.HCM | QSH | USSH | Xã hội – Nhân văn |
| 7 | ĐH Nông Lâm TP.HCM | QSF | NLU | Nông – Lâm – Ngư |
| 8 | ĐH Y Dược TP.HCM | QSM | UMP | Y – Dược |
| 9 | ĐH Tôn Đức Thắng | TDT | TDTU | Ngoài công lập lớn |
| 10 | ĐH Công nghệ Thông tin | QSI | UIT | CNTT chuyên sâu |
| 11 | ĐH Ngân hàng TP.HCM | BKH | HUB | Tài chính – Ngân hàng |
| 12 | ĐH Luật TP.HCM | HCL | UEL | Luật |
| 13 | ĐH Mở TP.HCM | MHC | OU | Đa ngành |
| 14 | ĐH Văn Lang | VLA | VLU | Tư thục lớn |
| 15 | ĐH Cần Thơ | CTU | CTU | Đồng bằng sông Cửu Long |

### Khu vực Hà Nội & Miền Bắc

| STT | Tên trường | Mã trường | Tên viết tắt | Ghi chú |
|-----|-----------|-----------|-------------|---------|
| 16 | ĐH Quốc gia Hà Nội | QHX | VNU-HN | Hệ thống đại học |
| 17 | ĐH Bách khoa Hà Nội | BKA | HUST | Kỹ thuật hàng đầu |
| 18 | ĐH Kinh tế Quốc dân | KQD | NEU | Kinh tế hàng đầu phía Bắc |
| 19 | ĐH Ngoại thương Hà Nội | FTU | FTU | Kinh tế đối ngoại |
| 20 | ĐH Xây dựng Hà Nội | XDA | NUCE | Xây dựng – Kiến trúc |
| 21 | ĐH Y Hà Nội | YHN | HMU | Y khoa |
| 22 | ĐH Giao thông Vận tải Hà Nội | GTV | UTC | Giao thông – Vận tải |
| 23 | ĐH Nông nghiệp Hà Nội | NNA | VNUA | Nông nghiệp |
| 24 | ĐH Sư phạm Hà Nội 1 | SPH | HNUE | Sư phạm |
| 25 | ĐH Luật Hà Nội | LHN | HLU | Luật |
| 26 | ĐH Công nghệ – ĐHQGHN | QHI | UET | CNTT – Kỹ thuật |
| 27 | ĐH Kinh tế – ĐHQGHN | QHE | UEB | Kinh tế |
| 28 | Học viện Công nghệ Bưu chính Viễn thông | PTA | PTIT | CNTT – Viễn thông |
| 29 | Học viện Kỹ thuật Mật mã | MCA | HVKTMật mã | An toàn thông tin |
| 30 | ĐH Thương mại | TMA | VCU | Thương mại |

### Khu vực Đà Nẵng & Miền Trung

| STT | Tên trường | Mã trường | Tên viết tắt | Ghi chú |
|-----|-----------|-----------|-------------|---------|
| 31 | ĐH Đà Nẵng | DNX | UD | Hệ thống đại học |
| 32 | ĐH Bách khoa Đà Nẵng | DAN | DUT | Kỹ thuật miền Trung |
| 33 | ĐH Kinh tế Đà Nẵng | DKT | DUE | Kinh tế miền Trung |
| 34 | ĐH Sư phạm Đà Nẵng | DSP | UED | Sư phạm miền Trung |
| 35 | ĐH Huế | HUX | HU | Hệ thống đại học Huế |
| 36 | ĐH Y Dược Huế | HYD | HUP | Y – Dược miền Trung |
| 37 | ĐH Vinh | VNA | VU | Nghệ An |
| 38 | ĐH Duy Tân | DTN | DTU | Tư thục lớn Đà Nẵng |
| ... | *(Bổ sung đến 50 trong quá trình triển khai)* | ... | ... | ... |

### Ghi chú về Seed Data

- **Thứ tự ưu tiên crawl:** Trường TP.HCM → Hà Nội → Đà Nẵng → các tỉnh khác
- **Mã trường** là mã do Bộ GD&ĐT cấp, dùng làm `university_code` trong DB
- Danh sách đầy đủ sẽ được lưu ở `craw-data/scripts/seed_universities.json` và cập nhật trong Sprint 0

---

## Phụ lục B – Checklist Khảo sát Nguồn Dữ liệu

> Bắt buộc hoàn thành checklist này **trước khi bắt đầu code** spider cho bất kỳ nguồn mới nào.  
> Mục đích: tránh viết code xong mới phát hiện nguồn không dùng được.

### Checklist chung (áp dụng cho mọi nguồn)

```
NGUỒN: ___________________________
URL:   ___________________________
Ngày khảo sát: ___________________
Người khảo sát: __________________

[ ] 1. Kiểm tra robots.txt
        URL: {domain}/robots.txt
        Kết quả: Disallow những path nào? _______________
        Nguồn có cho phép crawl không? [ ] Có  [ ] Không  [ ] Không rõ

[ ] 2. Yêu cầu xác thực
        Có cần đăng nhập để xem dữ liệu? [ ] Có  [ ] Không
        Nếu có → cân nhắc bỏ qua nguồn này

[ ] 3. Kiểm tra JavaScript rendering
        Mở DevTools > Network, reload trang
        Dữ liệu nằm trong HTML tĩnh? [ ] Có  [ ] Không (JS render)
        → Nếu JS render: dùng Playwright
        → Nếu HTML tĩnh: dùng Scrapy thuần

[ ] 4. Xác định URL pattern
        Pattern URL trang danh sách: ___________________________
        Pattern URL trang chi tiết:  ___________________________
        Có pagination không? [ ] Có  [ ] Không
        Nếu có, pattern trang N: ___________________________

[ ] 5. Xác định CSS/XPath selectors
        Selector container chính: ___________________________
        Selector tên trường/ngành: ___________________________
        Selector điểm/lương:       ___________________________
        Selector tổ hợp môn:       ___________________________
        (Ghi lại đầy đủ vào config/spider_config.py)

[ ] 6. Kiểm tra anti-bot
        Có Cloudflare / CAPTCHA không? [ ] Có  [ ] Không
        Rate limit bao nhiêu req/giây là an toàn? _____ req/s
        Cần rotate User-Agent? [ ] Có  [ ] Không
        Cần cookies / session? [ ] Có  [ ] Không

[ ] 7. Test thủ công
        Gọi thử 5 URL khác nhau bằng curl / browser
        Tất cả URL trả về dữ liệu đúng? [ ] Có  [ ] Không
        Ghi chú bất thường: ___________________________

[ ] 8. Đo hiệu năng
        Thời gian load trung bình 1 trang: _____ giây
        DOWNLOAD_DELAY đề xuất: _____ giây

[ ] 9. Xác nhận tính ổn định
        Dữ liệu có nhất quán qua nhiều lần reload? [ ] Có  [ ] Không
        Trang có bị lỗi 5xx thường xuyên? [ ] Có  [ ] Không

[ ] 10. Cập nhật tài liệu
        Đã ghi selectors vào config/spider_config.py? [ ] Có
        Đã commit checklist lên Git? [ ] Có
```

---

### Kết quả khảo sát các nguồn chính

| Nguồn | JS Render | Anti-bot | robots.txt | DOWNLOAD_DELAY | Trạng thái |
|-------|-----------|----------|------------|----------------|------------|
| tuyensinh247.com | ❌ HTML tĩnh | Thấp | Cho phép | 1.5s | ✅ Sẵn sàng |
| diemthi.tuyensinh247.com | ❌ HTML tĩnh | Thấp | Cho phép | 1.5s | ✅ Sẵn sàng |
| tuyensinh.moet.gov.vn | ❌ HTML tĩnh | Thấp | Cho phép | 2.0s | ✅ Sẵn sàng |
| topcv.vn | ✅ JS render | Trung bình | Hạn chế | 3.0s | 🟡 Cần Playwright |
| vietnamworks.com | ✅ JS render | Cao | Hạn chế | 3.5s | 🟡 Cần Playwright + proxy |
| careerbuilder.vn | ✅ JS render | Trung bình | Cho phép | 2.5s | 🟡 Cần Playwright |

> **Lưu ý:** Kết quả khảo sát trên là tại thời điểm lập kế hoạch.  
> Dev cần **xác minh lại** trước khi bắt đầu Sprint tương ứng vì website có thể thay đổi.

---

## Phụ lục C – Bảng Mapping Holland RIASEC mặc định

> Dùng làm seed cho `EnrichmentPipeline`. Admin review và chỉnh sửa qua UC20.

| Mã Holland | Tên | Từ khóa nhận diện trong tên/mô tả ngành |
|------------|-----|------------------------------------------|
| **R** | Realistic – Thực tế | Kỹ thuật, Cơ khí, Điện, Điện tử, Xây dựng, Hàng hải, Cơ điện tử, Lâm nghiệp, Thú y |
| **I** | Investigative – Nghiên cứu | Khoa học, Nghiên cứu, Công nghệ, Toán, Vật lý, Hóa học, Sinh học, Dược, Y khoa |
| **A** | Artistic – Sáng tạo | Thiết kế, Mỹ thuật, Kiến trúc, Âm nhạc, Báo chí, Truyền thông, Điện ảnh, Ngôn ngữ |
| **S** | Social – Xã hội | Giáo dục, Sư phạm, Y tế, Công tác xã hội, Tâm lý, Du lịch, Khách sạn, Nhà hàng |
| **E** | Enterprising – Dẫn dắt | Kinh doanh, Quản trị, Marketing, Luật, Ngoại thương, Logistics, Bất động sản |
| **C** | Conventional – Quy củ | Kế toán, Kiểm toán, Tài chính, Thống kê, Hành chính, Thư viện, Lưu trữ |

### Ví dụ mapping một số ngành phổ biến

| Ngành | Mã ngành | Holland Types |
|-------|---------|---------------|
| Kỹ thuật Phần mềm | 7480103 | I, R |
| Khoa học Máy tính | 7480101 | I, R |
| Quản trị Kinh doanh | 7340101 | E, C |
| Y đa khoa | 7720101 | I, S |
| Kiến trúc | 7580101 | A, R |
| Sư phạm Toán | 7140209 | I, S |
| Luật | 7380101 | E, C |
| Công tác Xã hội | 7760101 | S, E |
| Kế toán | 7340301 | C, E |
| Thiết kế Đồ họa | 7210403 | A, I |

> **Quy tắc:** Mỗi ngành có tối đa 3 Holland types, xếp theo mức độ phù hợp giảm dần.

---

*Phụ lục thuộc về tài liệu: [README – Kế hoạch Thu thập Dữ liệu](./README.md)*  
*Cập nhật lần cuối: 2025 | NLU-EduPath*