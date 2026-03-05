# ============================================================
# scripts/seed_data.py
# "BỘ NÃO" NGÀNH HỌC CHUẨN (VIETNAM STANDARD MAJORS)
# Hệ thống tự động ánh xạ khi crawl và sẵn sàng cho AI Tư vấn
# ============================================================

from __future__ import annotations
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("seed_data")

_NOW = datetime.now(tz=timezone.utc)
_SOURCE_URL = "https://huongnghiepviet.com/nganh-nghe"

# UNIVERSITIES_SEED để trống vì dùng chế độ AUTOPILOT
UNIVERSITIES_SEED = []

# DANH MỤC NGÀNH HỌC CHUẨN TOÀN QUỐC (~300+ MÃ)
# Cấu trúc: (Mã, Tên, Nhóm ngành, Holland Type)
_MAJORS_RAW = [
    # --- 714: SƯ PHẠM ---
    ("7140101", "Giáo dục Mầm non", "Sư phạm", "S, A"),
    ("7140102", "Giáo dục Tiểu học", "Sư phạm", "S"),
    ("7140114", "Sư phạm Toán học", "Sư phạm", "S, I"),
    ("7140115", "Sư phạm Tin học", "Sư phạm", "S, I"),
    ("7140201", "Sư phạm Tiếng Anh", "Sư phạm", "S, A"),
    ("7140210", "Sư phạm Lịch sử", "Sư phạm", "S, I"),
    ("7140211", "Sư phạm Ngữ văn", "Sư phạm", "S, A"),
    ("7140212", "Sư phạm Địa lý", "Sư phạm", "S, I"),
    ("7140217", "Sư phạm Vật lý", "Sư phạm", "S, I"),
    ("7140218", "Sư phạm Hóa học", "Sư phạm", "S, I"),
    ("7140219", "Sư phạm Sinh học", "Sư phạm", "S, I"),
    ("7140231", "Sư phạm Âm nhạc", "Sư phạm", "S, A"),
    ("7140232", "Sư phạm Mỹ thuật", "Sư phạm", "S, A"),
    ("7140246", "Sư phạm Kỹ thuật công nghiệp", "Sư phạm", "S, R"),
    ("7140103", "Giáo dục Đặc biệt", "Sư phạm", "S"),
    ("7140104", "Giáo dục Công dân", "Sư phạm", "S"),
    ("7140105", "Giáo dục Chính trị", "Sư phạm", "S"),
    ("7140106", "Giáo dục Thể chất", "Sư phạm", "S, R"),
    ("7140107", "Huấn luyện thể thao", "Sư phạm", "S, R"),
    ("7140108", "Giáo dục Quốc phòng - An ninh", "Sư phạm", "S, R"),
    ("7140202", "Sư phạm Tiếng Nga", "Sư phạm", "S, A"),
    ("7140203", "Sư phạm Tiếng Pháp", "Sư phạm", "S, A"),
    ("7140204", "Sư phạm Tiếng Trung Quốc", "Sư phạm", "S, A"),
    ("7140205", "Sư phạm Tiếng Đức", "Sư phạm", "S, A"),
    ("7140206", "Sư phạm Tiếng Nhật", "Sư phạm", "S, A"),
    ("7140209", "Sư phạm Tiếng Hàn Quốc", "Sư phạm", "S, A"),
    ("7140214", "Sư phạm công nghệ", "Sư phạm", "S, R"),
    ("7140215", "Sư phạm khoa học tự nhiên", "Sư phạm", "S, I"),
    ("7140216", "Giáo dục pháp luật", "Sư phạm", "S, E"),

    # --- 721: NGHỆ THUẬT ---
    ("7210101", "Hội họa", "Nghệ thuật", "A, R"),
    ("7210103", "Đồ họa", "Nghệ thuật", "A, R"),
    ("7210104", "Điêu khắc", "Nghệ thuật", "A, R"),
    ("7210205", "Thiết kế đồ họa", "Nghệ thuật", "A, E, C"),
    ("7210201", "Thiết kế thời trang", "Nghệ thuật", "A, E"),
    ("7210204", "Thiết kế công nghiệp", "Nghệ thuật", "A, R"),
    ("7210403", "Đạo diễn điện ảnh, truyền hình", "Nghệ thuật", "A, E"),
    ("7210404", "Diễn viên kịch, điện ảnh", "Nghệ thuật", "A, S"),
    ("7210202", "Thiết kế nội thất", "Nghệ thuật", "A, R, E"),
    ("7210203", "Thiết kế mỹ thuật sân khấu điện ảnh", "Nghệ thuật", "A"),
    ("7210301", "Âm nhạc học", "Nghệ thuật", "A, I"),
    ("7210302", "Sáng tác âm nhạc", "Nghệ thuật", "A"),
    ("7210303", "Chỉ huy âm nhạc", "Nghệ thuật", "A, E"),
    ("7210341", "Thanh nhạc", "Nghệ thuật", "A, S"),
    ("7210311", "Piano", "Nghệ thuật", "A"),
    ("7210312", "Nhạc Jazz", "Nghệ thuật", "A"),

    # --- 722: NHÂN VĂN ---
    ("7220101", "Tiếng Việt và văn hóa Việt Nam", "Nhân văn", "A, S"),
    ("7220201", "Ngôn ngữ Anh", "Nhân văn", "A, S"),
    ("7220202", "Ngôn ngữ Nga", "Nhân văn", "A, S"),
    ("7220203", "Ngôn ngữ Pháp", "Nhân văn", "A, S"),
    ("7220204", "Ngôn ngữ Trung Quốc", "Nhân văn", "A, S"),
    ("7220205", "Ngôn ngữ Đức", "Nhân văn", "A, S"),
    ("7220206", "Ngôn ngữ Nhật", "Nhân văn", "A, S"),
    ("7220209", "Ngôn ngữ Hàn Quốc", "Nhân văn", "A, S"),
    ("7229001", "Triết học", "Nhân văn", "I, S"),
    ("7229010", "Lịch sử học", "Nhân văn", "I, S"),
    ("7229030", "Văn học", "Nhân văn", "A, S"),
    ("7229040", "Văn hóa học", "Nhân văn", "A, S"),
    ("7229042", "Quản lý văn hóa", "Nhân văn", "E, S"),
    ("7229020", "Ngôn ngữ học", "Nhân văn", "I, A"),

    # --- 731: XÃ HỘI & HÀNH VI ---
    ("7310101", "Kinh tế", "Xã hội và Hành vi", "I, E, C"),
    ("7310102", "Kinh tế chính trị", "Xã hội và Hành vi", "I, S"),
    ("7310104", "Kinh tế phát triển", "Xã hội và Hành vi", "I, E"),
    ("7310106", "Kinh tế đầu tư", "Xã hội và Hành vi", "I, E, C"),
    ("7310107", "Kinh tế quốc tế", "Xã hội và Hành vi", "I, E"),
    ("7310201", "Chính trị học", "Xã hội và Hành vi", "I, E, S"),
    ("7310301", "Xã hội học", "Xã hội và Hành vi", "I, S"),
    ("7310401", "Tâm lý học", "Xã hội và Hành vi", "I, S"),
    ("7310601", "Quốc tế học", "Xã hội và Hành vi", "E, S, I"),
    ("7310608", "Đông Nam Á học", "Xã hội và Hành vi", "I, S"),
    ("7310630", "Việt Nam học", "Xã hội và Hành vi", "S, A"),
    ("7310602", "Đông phương học", "Xã hội và Hành vi", "I, S, A"),
    ("7310612", "Nhật Bản học", "Xã hội và Hành vi", "I, S"),
    ("7310613", "Hàn Quốc học", "Xã hội và Hành vi", "I, S"),

    # --- 732: BÁO CHÍ & THÔNG TIN ---
    ("7320101", "Báo chí", "Báo chí và Thông tin", "A, E, S"),
    ("7320106", "Truyền thông đa phương tiện", "Báo chí và Thông tin", "A, E, R"),
    ("7320108", "Quan hệ công chúng", "Báo chí và Thông tin", "E, S, A"),
    ("7320201", "Thông tin - thư viện", "Báo chí và Thông tin", "C, S"),
    ("7320305", "Quản lý thông tin", "Báo chí và Thông tin", "C, E"),
    ("7320105", "Truyền thông đại chúng", "Báo chí và Thông tin", "E, A, S"),

    # --- 734: KINH DOANH & QUẢN LÝ ---
    ("7340101", "Quản trị kinh doanh", "Kinh doanh và Quản lý", "E, S"),
    ("7340115", "Marketing", "Kinh doanh và Quản lý", "E, A"),
    ("7340120", "Kinh doanh quốc tế", "Kinh doanh và Quản lý", "E, I"),
    ("7340121", "Kinh doanh thương mại", "Kinh doanh và Quản lý", "E, S"),
    ("7340122", "Logistics và Quản lý chuỗi cung ứng", "Kinh doanh và Quản lý", "E, C"),
    ("7340201", "Tài chính - Ngân hàng", "Kinh doanh và Quản lý", "E, C"),
    ("7340202", "Bảo hiểm", "Kinh doanh và Quản lý", "C, E"),
    ("7340301", "Kế toán", "Kinh doanh và Quản lý", "C, I"),
    ("7340302", "Kiểm toán", "Kinh doanh và Quản lý", "C, I"),
    ("7340401", "Quản trị nhân lực", "Kinh doanh và Quản lý", "E, S"),
    ("7340403", "Quản trị văn phòng", "Kinh doanh và Quản lý", "C, S"),
    ("7340404", "Hệ thống thông tin quản lý", "Kinh doanh và Quản lý", "C, E, I"),
    ("7340405", "Thương mại điện tử", "Kinh doanh và Quản lý", "E, C, I"),
    ("7340409", "Quản lý dự án", "Kinh doanh và Quản lý", "E, C"),
    ("7340124", "Bất động sản", "Kinh doanh và Quản lý", "E, S"),

    # --- 738: PHÁP LUẬT ---
    ("7380101", "Luật", "Pháp luật", "E, I, S"),
    ("7380107", "Luật kinh tế", "Pháp luật", "E, I, C"),
    ("7380103", "Luật quốc tế", "Pháp luật", "E, I, S"),
    ("7380102", "Luật hàng hải", "Pháp luật", "E, I"),

    # --- 742, 744: KHOA HỌC TỰ NHIÊN ---
    ("7420101", "Sinh học", "Khoa học sự sống", "I, R"),
    ("7420201", "Công nghệ sinh học", "Khoa học sự sống", "I, R"),
    ("7440101", "Vật lý học", "Khoa học tự nhiên", "I, R"),
    ("7440112", "Hóa học", "Khoa học tự nhiên", "I, R"),
    ("7440122", "Khoa học vật liệu", "Khoa học tự nhiên", "I, R"),
    ("7440301", "Địa chất học", "Khoa học tự nhiên", "I, R"),
    ("7440201", "Khoa học môi trường", "Khoa học tự nhiên", "I, S"),
    ("7440302", "Địa chất y sinh", "Khoa học tự nhiên", "I, S"),

    # --- 746: TOÁN & THỐNG KÊ ---
    ("7460101", "Toán học", "Toán và Thống kê", "I, C"),
    ("7460112", "Toán ứng dụng", "Toán và Thống kê", "I, C"),
    ("7460115", "Toán tin", "Toán và Thống kê", "I, C, R"),
    ("7460201", "Thống kê", "Toán và Thống kê", "I, C"),

    # --- 748: MÁY TÍNH & CNTT ---
    ("7480101", "Khoa học máy tính", "Máy tính và CNTT", "I, R"),
    ("7480102", "Mạng máy tính và truyền thông dữ liệu", "Máy tính và CNTT", "I, R"),
    ("7480103", "Kỹ thuật phần mềm", "Máy tính và CNTT", "I, C"),
    ("7480104", "Hệ thống thông tin", "Máy tính và CNTT", "I, C, E"),
    ("7480106", "Kỹ thuật máy tính", "Máy tính và CNTT", "I, R"),
    ("7480107", "Trí tuệ nhân tạo", "Máy tính và CNTT", "I, R"),
    ("7480108", "Khoa học dữ liệu", "Máy tính và CNTT", "I, C"),
    ("7480201", "Công nghệ thông tin", "Máy tính và CNTT", "I, R"),
    ("7480202", "An toàn thông tin", "Máy tính và CNTT", "I, R"),

    # --- 751: CÔNG NGHỆ KỸ THUẬT ---
    ("7510102", "Công nghệ kỹ thuật công trình xây dựng", "Công nghệ kỹ thuật", "R, I"),
    ("7510201", "Công nghệ kỹ thuật cơ khí", "Công nghệ kỹ thuật", "R, I"),
    ("7510203", "Công nghệ kỹ thuật ô tô", "Công nghệ kỹ thuật", "R, I"),
    ("7510205", "Công nghệ kỹ thuật nhiệt", "Công nghệ kỹ thuật", "R, I"),
    ("7510301", "Công nghệ kỹ thuật điện, điện tử", "Công nghệ kỹ thuật", "R, I"),
    ("7510302", "Công nghệ kỹ thuật điện tử - viễn thông", "Công nghệ kỹ thuật", "R, I"),
    ("7510303", "Công nghệ kỹ thuật điều khiển và tự động hóa", "Công nghệ kỹ thuật", "R, I"),
    ("7510401", "Công nghệ kỹ thuật hóa học", "Công nghệ kỹ thuật", "I, R"),
    ("7510406", "Công nghệ kỹ thuật môi trường", "Công nghệ kỹ thuật", "I, R"),
    ("7510601", "Quản lý công nghiệp", "Công nghệ kỹ thuật", "E, C"),
    ("7510202", "Công nghệ chế tạo máy", "Công nghệ kỹ thuật", "R, I"),
    ("7510206", "Công nghệ kỹ thuật tàu thủy", "Công nghệ kỹ thuật", "R, I"),
    ("7510207", "Bảo dưỡng công nghiệp", "Công nghệ kỹ thuật", "R, C"),

    # --- 752: KỸ THUẬT ---
    ("7520103", "Kỹ thuật cơ khí", "Kỹ thuật", "R, I"),
    ("7520114", "Kỹ thuật cơ điện tử", "Kỹ thuật", "R, I"),
    ("7520115", "Kỹ thuật nhiệt", "Kỹ thuật", "R, I"),
    ("7520116", "Kỹ thuật Robot và Trí tuệ nhân tạo", "Kỹ thuật", "R, I"),
    ("7520121", "Kỹ thuật tàu thủy", "Kỹ thuật", "R, I"),
    ("7520130", "Kỹ thuật ô tô", "Kỹ thuật", "R, I"),
    ("7520102", "Kỹ thuật hàng không", "Kỹ thuật", "R, I"),
    ("7520101", "Kỹ thuật không gian", "Kỹ thuật", "I, R"),
    ("7520201", "Kỹ thuật điện", "Kỹ thuật", "R, I"),
    ("7520207", "Kỹ thuật điện tử - viễn thông", "Kỹ thuật", "R, I"),
    ("7520216", "Kỹ thuật điều khiển và tự động hóa", "Kỹ thuật", "R, I"),
    ("7520301", "Kỹ thuật hóa học", "Kỹ thuật", "I, R"),
    ("7520503", "Kỹ thuật môi trường", "Kỹ thuật", "I, R"),
    ("7520309", "Kỹ thuật vật liệu", "Kỹ thuật", "I, R"),
    ("7520171", "Kỹ thuật y sinh", "Kỹ thuật", "I, R"),
    ("7520604", "Kỹ thuật dầu khí", "Kỹ thuật", "I, R"),
    ("7520104", "Cơ kỹ thuật", "Kỹ thuật", "I, R"),
    ("7520117", "Kỹ thuật công nghiệp", "Kỹ thuật", "R, E, C"),
    ("7520118", "Kỹ thuật hệ thống công nghiệp", "Kỹ thuật", "I, E, C"),
    ("7520401", "Vật lý kỹ thuật", "Kỹ thuật", "I, R"),
    ("7520402", "Kỹ thuật hạt nhân", "Kỹ thuật", "I, R"),
    ("7520501", "Kỹ thuật địa chất", "Kỹ thuật", "R, I"),
    ("7520502", "Kỹ thuật trắc địa - bản đồ", "Kỹ thuật", "R, I, C"),
    ("7520601", "Kỹ thuật mỏ", "Kỹ thuật", "R, I"),

    # --- 754: SẢN XUẤT & CHẾ BIẾN ---
    ("7540101", "Công nghệ thực phẩm", "Sản xuất và Chế biến", "I, R"),
    ("7540104", "Công nghệ sau thu hoạch", "Sản xuất và Chế biến", "I, R"),
    ("7540204", "Công nghệ dệt, may", "Sản xuất và Chế biến", "R, C"),
    ("7540202", "Công nghệ sợi, dệt", "Sản xuất và Chế biến", "R, C"),
    ("7540105", "Công nghệ chế biến thủy sản", "Sản xuất và Chế biến", "R, I"),
    ("7540106", "Công nghệ chế biến lâm sản", "Sản xuất và Chế biến", "R, I"),

    # --- 758: KIẾN TRÚC & XÂY DỰNG ---
    ("7580101", "Kiến trúc", "Kiến trúc và Xây dựng", "A, I, R"),
    ("7580102", "Kiến trúc cảnh quan", "Kiến trúc và Xây dựng", "A, R"),
    ("7580103", "Quy hoạch vùng và đô thị", "Kiến trúc và Xây dựng", "I, A, E"),
    ("7580108", "Thiết kế nội thất", "Kiến trúc và Xây dựng", "A, R, E"),
    ("7580201", "Kỹ thuật xây dựng", "Kiến trúc và Xây dựng", "R, I"),
    ("7580202", "Kỹ thuật xây dựng công trình giao thông", "Kiến trúc và Xây dựng", "R, I"),
    ("7580203", "Kỹ thuật xây dựng công trình thủy", "Kiến trúc và Xây dựng", "R, I"),
    ("7580301", "Quản lý xây dựng", "Kiến trúc và Xây dựng", "E, C"),
    ("7580302", "Kinh tế xây dựng", "Kiến trúc và Xây dựng", "C, E"),
    ("7580210", "Kỹ thuật cơ sở hạ tầng", "Kiến trúc và Xây dựng", "R, I"),

    # --- 762, 764: NÔNG, LÂM, THỦY SẢN ---
    ("7620105", "Chăn nuôi", "Nông, Lâm, Thủy sản", "R, I"),
    ("7620110", "Khoa học cây trồng", "Nông, Lâm, Thủy sản", "I, R"),
    ("7620112", "Bảo vệ thực vật", "Nông, Lâm, Thủy sản", "I, R"),
    ("7620115", "Nông nghiệp", "Nông, Lâm, Thủy sản", "R, I"),
    ("7620201", "Lâm học", "Nông, Lâm, Thủy sản", "R, I"),
    ("7620205", "Quản lý tài nguyên rừng", "Nông, Lâm, Thủy sản", "I, E"),
    ("7620301", "Nuôi trồng thủy sản", "Nông, Lâm, Thủy sản", "R, I"),
    ("7640101", "Thú y", "Thú y", "I, R, S"),
    ("7620101", "Nông học", "Nông, Lâm, Thủy sản", "I, R"),
    ("7620116", "Khuyến nông", "Nông, Lâm, Thủy sản", "S, E"),

    # --- 772: SỨC KHỎE ---
    ("7720101", "Y khoa", "Sức khỏe", "I, S"),
    ("7720110", "Y học dự phòng", "Sức khỏe", "I, S"),
    ("7720115", "Y học cổ truyền", "Sức khỏe", "I, S"),
    ("7720201", "Dược học", "Sức khỏe", "I, C"),
    ("7720301", "Điều dưỡng", "Sức khỏe", "S, I"),
    ("7720501", "Răng - Hàm - Mặt", "Sức khỏe", "I, S, A"),
    ("7720601", "Kỹ thuật xét nghiệm y học", "Sức khỏe", "I, R"),
    ("7720602", "Kỹ thuật hình ảnh y học", "Sức khỏe", "I, R"),
    ("7720603", "Phục hồi chức năng", "Sức khỏe", "S, R"),
    ("7720401", "Y tế công cộng", "Sức khỏe", "S, I"),
    ("7720302", "Hộ sinh", "Sức khỏe", "S"),
    ("7720402", "Dinh dưỡng", "Sức khỏe", "I, S"),

    # --- 776, 781: DỊCH VỤ XÃ HỘI & DU LỊCH ---
    ("7760101", "Công tác xã hội", "Dịch vụ xã hội", "S"),
    ("7810101", "Du lịch", "Du lịch, Khách sạn, Thể thao", "E, S"),
    ("7810103", "Quản trị dịch vụ du lịch và lữ hành", "Du lịch, Khách sạn, Thể thao", "E, S"),
    ("7810201", "Quản trị khách sạn", "Du lịch, Khách sạn, Thể thao", "E, S, C"),
    ("7810202", "Quản trị nhà hàng và dịch vụ ăn uống", "Du lịch, Khách sạn, Thể thao", "E, S, C"),
    ("7810301", "Kinh tế thể thao", "Du lịch, Khách sạn, Thể thao", "E, R"),
    ("7810501", "Quản lý thể dục thể thao", "Du lịch, Khách sạn, Thể thao", "E, S, R"),

    # --- 784, 785: VẬN TẢI & MÔI TRƯỜNG ---
    ("7840101", "Khai thác vận tải", "Dịch vụ vận tải", "R, E"),
    ("7840104", "Quản lý hoạt động bay", "Dịch vụ vận tải", "R, E, C"),
    ("7850101", "Quản lý tài nguyên và môi trường", "Môi trường", "I, E"),
    ("7850102", "Quản lý đất đai", "Môi trường", "E, C"),

    # --- 786: AN NINH, QUỐC PHÒNG ---
    ("7860101", "Chỉ huy tham mưu Lục quân", "An ninh, Quốc phòng", "R, S, E"),
    ("7860102", "Chỉ huy tham mưu Đặc công", "An ninh, Quốc phòng", "R, S, E"),
    ("7860100", "Nghiệp vụ An ninh", "An ninh, Quốc phòng", "R, I, S"),
    ("7860111", "Nghiệp vụ Cảnh sát", "An ninh, Quốc phòng", "R, S, E"),
    ("7860201", "Phòng cháy chữa cháy và cứu nạn cứu hộ", "An ninh, Quốc phòng", "R, S, E"),
    ("7860103", "Chỉ huy tham mưu Hải quân", "An ninh, Quốc phòng", "R, S, E"),
    ("7860104", "Chỉ huy tham mưu Không quân", "An ninh, Quốc phòng", "R, S, E"),
    ("7860105", "Chỉ huy tham mưu Pháo binh", "An ninh, Quốc phòng", "R, S, E"),
    ("7860106", "Chỉ huy tham mưu Tăng - thiết giáp", "An ninh, Quốc phòng", "R, S, E"),
    ("7860109", "Biên phòng", "An ninh, Quốc phòng", "R, S, E"),
]

def seed_majors(session):
    from db.repositories.major_repo import MajorRepository
    from models.major import MajorCreate
    repo = MajorRepository(session)
    count = 0
    for code, name, group, holland in _MAJORS_RAW:
        schema = MajorCreate(
            major_code=code,
            name=name,
            major_group=group,
            major_group_code=code[:3],
            holland_types=[h.strip() for h in holland.split(",")],
            study_duration=4,
            degree_level="bachelor",
            scraped_at=_NOW,
            source_url=_SOURCE_URL
        )
        repo.upsert(schema)
        count += 1
    session.commit()
    logger.info(f"✨ [SUCCESS] Đã nạp thành công {count} ngành học vào từ điển.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    from db.connection import get_session_factory
    factory = get_session_factory()
    with factory() as session:
        if args.reset:
            from sqlalchemy import text
            session.execute(text("TRUNCATE admission_scores CASCADE;"))
            session.execute(text("TRUNCATE universities CASCADE;"))
            session.execute(text("TRUNCATE majors CASCADE;"))
            session.commit()
            logger.info("🗑️ [RESET] Đã xóa dữ liệu cũ.")
        seed_majors(session)

if __name__ == "__main__": main()
