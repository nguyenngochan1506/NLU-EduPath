# ============================================================
# config/holland_mapping.py
# Bảng mapping Holland RIASEC Types → ngành học
#
# Holland Types (RIASEC):
#   R = Realistic      – Thực tế, kỹ thuật, thao tác công cụ
#   I = Investigative  – Nghiên cứu, phân tích, tư duy logic
#   A = Artistic       – Sáng tạo, biểu đạt, nghệ thuật
#   S = Social         – Hỗ trợ, giảng dạy, quan hệ con người
#   E = Enterprising   – Lãnh đạo, kinh doanh, thuyết phục
#   C = Conventional   – Tổ chức, quy trình, chi tiết
#
# Career Anchors (Edgar Schein):
#   TF = Technical/Functional Competence
#   GM = General Managerial Competence
#   AU = Autonomy/Independence
#   SE = Security/Stability
#   EC = Entrepreneurial Creativity
#   SV = Service/Dedication to a Cause
#   CH = Pure Challenge
#   LI = Lifestyle Integration
#
# Cách dùng:
#   from config.holland_mapping import HollandMapper
#   mapper = HollandMapper()
#   result = mapper.get_holland_types("Kỹ thuật phần mềm")
#   # → {"holland_types": ["I", "R"], "career_anchor_tags": ["Technical/Functional Competence"]}
# ============================================================

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# CAREER ANCHOR CONSTANTS
# ============================================================

CA_TECHNICAL = "Technical/Functional Competence"
CA_MANAGERIAL = "General Managerial Competence"
CA_AUTONOMY = "Autonomy/Independence"
CA_SECURITY = "Security/Stability"
CA_ENTREPRENEURIAL = "Entrepreneurial Creativity"
CA_SERVICE = "Service/Dedication to a Cause"
CA_CHALLENGE = "Pure Challenge"
CA_LIFESTYLE = "Lifestyle Integration"


# ============================================================
# DATACLASS: HollandProfile
# ============================================================


@dataclass
class HollandProfile:
    """
    Hồ sơ Holland cho một nhóm ngành.

    Attributes:
        holland_types:     Danh sách mã Holland (tối đa 3, theo thứ tự ưu tiên)
        career_anchors:    Danh sách Career Anchor tags
        keywords:          Từ khóa để khớp với tên ngành (không dấu, lowercase)
        major_codes:       Danh sách mã ngành cụ thể (7 chữ số) để khớp chính xác
        description:       Mô tả ngắn về nhóm ngành (tiếng Việt)
    """

    holland_types: list[str]
    career_anchors: list[str]
    keywords: list[str] = field(default_factory=list)
    major_codes: list[str] = field(default_factory=list)
    description: str = ""


# ============================================================
# MASTER MAPPING TABLE
# Mỗi entry đại diện cho một nhóm ngành có đặc điểm Holland tương đồng.
# Thứ tự quan trọng: entry đặc biệt hơn nên đứng TRÊN entry tổng quát.
# ============================================================

HOLLAND_PROFILES: list[HollandProfile] = [

    # ──────────────────────────────────────────────────────────
    # NHÓM 1: Công nghệ thông tin & Kỹ thuật phần mềm
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["I", "R", "C"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "ky thuat phan mem",
            "software engineering",
            "cong nghe phan mem",
            "lap trinh",
            "phat trien phan mem",
        ],
        major_codes=["7480103", "7480201"],
        description="Kỹ thuật phần mềm, lập trình, phát triển ứng dụng",
    ),
    HollandProfile(
        holland_types=["I", "R", "C"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "cong nghe thong tin",
            "information technology",
            "khoa hoc may tinh",
            "computer science",
            "tin hoc",
            "ky thuat may tinh",
            "computer engineering",
            "mang may tinh",
            "an toan thong tin",
            "bao mat",
            "cybersecurity",
            "tri tue nhan tao",
            "artificial intelligence",
            "hoc may",
            "machine learning",
            "data science",
            "khoa hoc du lieu",
            "he thong thong tin",
            "cong nghe web",
            "ky thuat phan cung",
            "dien tu tin hoc",
        ],
        major_codes=[
            "7480201", "7480202", "7480203", "7480204", "7480205",
            "7480206", "7480207", "7480208", "7480209", "7480210",
        ],
        description="Công nghệ thông tin, khoa học máy tính, an toàn thông tin",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 2: Kỹ thuật điện – điện tử – tự động hóa
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["R", "I", "C"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "ky thuat dien",
            "dien tu",
            "vien thong",
            "tu dong hoa",
            "automation",
            "robot",
            "co dien tu",
            "mechatronics",
            "dieu khien",
            "ky thuat dieu khien",
            "dien cong nghiep",
        ],
        major_codes=[
            "7520201", "7520203", "7520204", "7520205",
            "7520207", "7520213", "7520301",
        ],
        description="Kỹ thuật điện, điện tử, viễn thông, tự động hóa",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 3: Kỹ thuật cơ khí – chế tạo – vật liệu
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["R", "I", "C"],
        career_anchors=[CA_TECHNICAL, CA_SECURITY],
        keywords=[
            "co khi",
            "che tao may",
            "ky thuat co khi",
            "vat lieu",
            "luyen kim",
            "co khi chenh",
            "nhiet lanh",
            "ky thuat nhiet",
            "ky thuat che tao",
            "oto",
            "ky thuat o to",
            "hang khong",
        ],
        major_codes=[
            "7520101", "7520103", "7520104", "7520110",
            "7520114", "7520117", "7520125", "7520130",
        ],
        description="Kỹ thuật cơ khí, chế tạo máy, vật liệu, ô tô",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 4: Xây dựng – Kiến trúc – Quy hoạch
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["R", "A", "I"],
        career_anchors=[CA_TECHNICAL, CA_AUTONOMY],
        keywords=[
            "xay dung",
            "civil engineering",
            "kien truc",
            "architecture",
            "quy hoach",
            "do thi",
            "cong trinh",
            "ket cau",
            "giao thong",
            "thuy loi",
            "moi truong xay dung",
        ],
        major_codes=[
            "7580101", "7580102", "7580103", "7580104",
            "7580105", "7580106", "7580110", "7580201",
            "7580202",
        ],
        description="Xây dựng, kiến trúc, quy hoạch đô thị, giao thông",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 5: Kinh tế – Quản trị – Tài chính
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["E", "C", "I"],
        career_anchors=[CA_MANAGERIAL, CA_ENTREPRENEURIAL],
        keywords=[
            "quan tri kinh doanh",
            "business administration",
            "mba",
            "quan tri",
            "kinh doanh quoc te",
            "thuong mai quoc te",
            "marketing",
            "quan tri ban hang",
            "thuong mai dien tu",
            "e-commerce",
        ],
        major_codes=[
            "7340101", "7340102", "7340120", "7340121",
            "7340122", "7340123",
        ],
        description="Quản trị kinh doanh, marketing, thương mại",
    ),
    HollandProfile(
        holland_types=["C", "I", "E"],
        career_anchors=[CA_SECURITY, CA_TECHNICAL],
        keywords=[
            "ke toan",
            "accounting",
            "kiem toan",
            "auditing",
            "tai chinh",
            "finance",
            "ngan hang",
            "banking",
            "chung khoan",
            "bao hiem",
            "insurance",
            "tai chinh ngan hang",
        ],
        major_codes=[
            "7340201", "7340301", "7340302", "7340303",
        ],
        description="Kế toán, kiểm toán, tài chính, ngân hàng, chứng khoán",
    ),
    HollandProfile(
        holland_types=["I", "C", "E"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "kinh te",
            "economics",
            "kinh te hoc",
            "kinh te chinh tri",
            "kinh te phat trien",
            "kinh te quoc te",
            "thuong mai",
            "kinh doanh",
        ],
        major_codes=[
            "7310101", "7310106", "7310108",
        ],
        description="Kinh tế học, kinh tế phát triển, kinh tế quốc tế",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 6: Luật – Hành chính – Chính trị
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["E", "S", "C"],
        career_anchors=[CA_SERVICE, CA_MANAGERIAL],
        keywords=[
            "luat",
            "law",
            "luat kinh te",
            "luat dan su",
            "luat hinh su",
            "luat quoc te",
            "quan li nha nuoc",
            "hanh chinh",
            "chinh sach cong",
            "khoa hoc chinh tri",
        ],
        major_codes=[
            "7380101", "7380104", "7380107", "7380108",
            "7310201", "7310205",
        ],
        description="Luật, hành chính công, chính sách công, khoa học chính trị",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 7: Sư phạm – Giáo dục
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["S", "A", "I"],
        career_anchors=[CA_SERVICE, CA_LIFESTYLE],
        keywords=[
            "su pham",
            "education",
            "giao duc",
            "su pham toan",
            "su pham vat ly",
            "su pham hoa hoc",
            "su pham sinh hoc",
            "su pham tin hoc",
            "su pham nguyen van",
            "giao duc tieu hoc",
            "giao duc mam non",
            "su pham ngoai ngu",
        ],
        major_codes=[
            "7140201", "7140202", "7140203", "7140204",
            "7140205", "7140206", "7140207", "7140208",
            "7140209", "7140210", "7140211", "7140212",
        ],
        description="Sư phạm, giáo dục các cấp, giảng dạy bộ môn",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 8: Y – Dược – Sức khỏe
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["I", "S", "R"],
        career_anchors=[CA_SERVICE, CA_TECHNICAL],
        keywords=[
            "y khoa",
            "medicine",
            "bac si",
            "y da khoa",
            "y hoc",
            "y te",
            "benh hoc",
            "noi khoa",
            "ngoai khoa",
            "nhi khoa",
            "rang ham mat",
            "mat",
            "tai mui hong",
        ],
        major_codes=[
            "7720101", "7720102", "7720104", "7720105",
            "7720107", "7720109",
        ],
        description="Y khoa, bác sĩ đa khoa, y học lâm sàng",
    ),
    HollandProfile(
        holland_types=["I", "R", "S"],
        career_anchors=[CA_TECHNICAL, CA_SERVICE],
        keywords=[
            "duoc",
            "pharmacy",
            "duoc hoc",
            "duoc ly",
            "ky thuat y hoc",
            "xet nghiem",
            "chan doan hinh anh",
            "phuc hoi chuc nang",
            "dieu duong",
            "nursing",
        ],
        major_codes=[
            "7720201", "7720202", "7720301", "7720302",
            "7720303", "7720304",
        ],
        description="Dược học, điều dưỡng, kỹ thuật y học",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 9: Khoa học tự nhiên – Toán – Vật lý – Hóa học
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["I", "R", "C"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "toan hoc",
            "mathematics",
            "toan ung dung",
            "applied mathematics",
            "khoa hoc tinh toan",
            "thong ke",
            "statistics",
            "toan ly",
        ],
        major_codes=["7460101", "7460112"],
        description="Toán học, toán ứng dụng, thống kê, khoa học tính toán",
    ),
    HollandProfile(
        holland_types=["I", "R", "C"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "vat ly",
            "physics",
            "vat ly ky thuat",
            "quang hoc",
            "hat nhan",
            "vat lieu",
            "vat ly chat ran",
        ],
        major_codes=["7440102", "7440104", "7520207"],
        description="Vật lý, vật lý kỹ thuật, vật liệu",
    ),
    HollandProfile(
        holland_types=["I", "R", "C"],
        career_anchors=[CA_TECHNICAL, CA_CHALLENGE],
        keywords=[
            "hoa hoc",
            "chemistry",
            "hoa phan tich",
            "hoa huu co",
            "hoa vo co",
            "hoa ly",
            "hoa duoc",
        ],
        major_codes=["7440112", "7440113", "7440114"],
        description="Hóa học, hóa phân tích, hóa hữu cơ, hóa dược",
    ),
    HollandProfile(
        holland_types=["I", "R", "S"],
        career_anchors=[CA_TECHNICAL, CA_SERVICE],
        keywords=[
            "sinh hoc",
            "biology",
            "cong nghe sinh hoc",
            "biotechnology",
            "vi sinh",
            "microbiology",
            "di truyen",
            "sinh thai",
            "ecology",
            "quan ly tai nguyen",
        ],
        major_codes=[
            "7420101", "7420103", "7420201", "7420202",
            "7420301", "7420302",
        ],
        description="Sinh học, công nghệ sinh học, vi sinh học",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 10: Nông – Lâm – Ngư nghiệp
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["R", "I", "S"],
        career_anchors=[CA_TECHNICAL, CA_SECURITY],
        keywords=[
            "nong nghiep",
            "agriculture",
            "trong trot",
            "chan nuoi",
            "lam nghiep",
            "forestry",
            "ngu nghiep",
            "thuy san",
            "aquaculture",
            "bao ve thuc vat",
            "dat dai",
            "moi truong nong nghiep",
        ],
        major_codes=[
            "7620101", "7620102", "7620103", "7620105",
            "7620106", "7620110", "7620114", "7620115",
        ],
        description="Nông nghiệp, lâm nghiệp, thủy sản, bảo vệ thực vật",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 11: Môi trường – Địa chất – Tài nguyên
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["I", "R", "S"],
        career_anchors=[CA_SERVICE, CA_TECHNICAL],
        keywords=[
            "moi truong",
            "environment",
            "ky thuat moi truong",
            "khoa hoc moi truong",
            "bien doi khi hau",
            "dia chat",
            "geology",
            "tai nguyen",
            "dia ly",
            "geography",
            "gis",
            "ban do",
            "trac dia",
        ],
        major_codes=[
            "7440213", "7520320", "7440221",
            "7520501", "7520502", "7520503",
        ],
        description="Kỹ thuật môi trường, địa chất, tài nguyên thiên nhiên",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 12: Ngôn ngữ – Văn học – Báo chí – Truyền thông
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["A", "S", "I"],
        career_anchors=[CA_AUTONOMY, CA_SERVICE],
        keywords=[
            "bao chi",
            "journalism",
            "truyen thong",
            "media",
            "quan he cong chung",
            "public relations",
            "truyen thong da phuong tien",
            "quan he quoc te",
            "bao chi truyen thong",
        ],
        major_codes=[
            "7320101", "7320104", "7320106", "7320107",
        ],
        description="Báo chí, truyền thông đại chúng, quan hệ công chúng",
    ),
    HollandProfile(
        holland_types=["A", "S", "I"],
        career_anchors=[CA_AUTONOMY, CA_LIFESTYLE],
        keywords=[
            "ngoai ngu",
            "ngu van",
            "van hoc",
            "literature",
            "tieng anh",
            "english",
            "tieng nhat",
            "japanese",
            "tieng han",
            "korean",
            "tieng phap",
            "french",
            "tieng trung",
            "chinese",
            "ngon ngu anh",
            "bien phien dich",
            "dong phuong hoc",
        ],
        major_codes=[
            "7220201", "7220204", "7220210", "7220212",
            "7220214", "7220215", "7220216",
        ],
        description="Ngôn ngữ, văn học, ngoại ngữ, biên phiên dịch",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 13: Nghệ thuật – Thiết kế
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["A", "R", "I"],
        career_anchors=[CA_AUTONOMY, CA_ENTREPRENEURIAL],
        keywords=[
            "thiet ke",
            "design",
            "thiet ke do hoa",
            "graphic design",
            "thiet ke noi that",
            "interior design",
            "thiet ke san pham",
            "my thuat",
            "fine arts",
            "hoi hoa",
            "dieu khac",
            "thiet ke thoi trang",
            "fashion design",
            "am nhac",
            "music",
            "san khau",
            "dien anh",
            "film",
            "truyen hinh",
        ],
        major_codes=[
            "7210403", "7210404", "7210405", "7210502",
            "7229001", "7229010", "7229030", "7229080",
        ],
        description="Thiết kế đồ họa, mỹ thuật, thời trang, âm nhạc, điện ảnh",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 14: Xã hội học – Tâm lý – Công tác xã hội
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["S", "I", "A"],
        career_anchors=[CA_SERVICE, CA_LIFESTYLE],
        keywords=[
            "tam ly",
            "psychology",
            "tam ly hoc",
            "cong tac xa hoi",
            "social work",
            "xa hoi hoc",
            "sociology",
            "nhan hoc",
            "anthropology",
            "xa hoi",
        ],
        major_codes=[
            "7310301", "7310303", "7760101",
        ],
        description="Tâm lý học, công tác xã hội, xã hội học",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 15: Du lịch – Khách sạn – Nhà hàng
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["E", "S", "A"],
        career_anchors=[CA_LIFESTYLE, CA_SERVICE],
        keywords=[
            "du lich",
            "tourism",
            "khach san",
            "hotel",
            "nha hang",
            "restaurant",
            "am thuc",
            "dich vu",
            "hospitality",
            "lu hanh",
        ],
        major_codes=[
            "7810101", "7810201", "7810202", "7810203",
        ],
        description="Du lịch, quản trị khách sạn, nhà hàng, ẩm thực",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 16: Logistics – Quản lý chuỗi cung ứng
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["E", "C", "R"],
        career_anchors=[CA_MANAGERIAL, CA_SECURITY],
        keywords=[
            "logistics",
            "quan ly chuoi cung ung",
            "supply chain",
            "van tai",
            "giao nhan",
            "xuat nhap khau",
            "hai quan",
            "quan ly van hanh",
            "operations management",
        ],
        major_codes=[
            "7340115", "7510501", "7510600",
        ],
        description="Logistics, quản lý chuỗi cung ứng, vận tải, xuất nhập khẩu",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 17: Công nghệ thực phẩm – Hóa thực phẩm
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["I", "R", "C"],
        career_anchors=[CA_TECHNICAL, CA_SECURITY],
        keywords=[
            "cong nghe thuc pham",
            "food technology",
            "hoa thuc pham",
            "bao quan thuc pham",
            "ky thuat chien bien",
            "dinh duong",
            "nutrition",
        ],
        major_codes=[
            "7540101", "7540101",
        ],
        description="Công nghệ thực phẩm, dinh dưỡng, bảo quản thực phẩm",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 18: Quản lý – Quản lý công nghiệp – Quản lý dự án
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["E", "C", "I"],
        career_anchors=[CA_MANAGERIAL, CA_CHALLENGE],
        keywords=[
            "quan ly cong nghiep",
            "industrial management",
            "quan ly du an",
            "project management",
            "quan ly chat luong",
            "quality management",
            "ky thuat quan ly",
            "quan ly san xuat",
            "ky thuat he thong",
            "systems engineering",
        ],
        major_codes=[
            "7510601", "7510604",
        ],
        description="Quản lý công nghiệp, quản lý dự án, kỹ thuật hệ thống",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 19: Dầu khí – Năng lượng
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["R", "I", "C"],
        career_anchors=[CA_TECHNICAL, CA_SECURITY],
        keywords=[
            "dau khi",
            "petroleum",
            "nang luong",
            "energy",
            "nang luong tai tao",
            "renewable energy",
            "dien hat nhan",
            "nuclear",
            "ky thuat dau khi",
            "khai thac dau khi",
        ],
        major_codes=[
            "7520605", "7520607",
        ],
        description="Kỹ thuật dầu khí, năng lượng, năng lượng tái tạo",
    ),

    # ──────────────────────────────────────────────────────────
    # NHÓM 20: Khoa học thể dục thể thao
    # ──────────────────────────────────────────────────────────
    HollandProfile(
        holland_types=["R", "S", "E"],
        career_anchors=[CA_SERVICE, CA_LIFESTYLE],
        keywords=[
            "the duc",
            "the thao",
            "sports",
            "hlv",
            "huan luyen",
            "the duc the thao",
            "giao duc the chat",
        ],
        major_codes=[
            "7810301", "7810302",
        ],
        description="The duc the thao, co huan luyen vien, giao duc the chat",
    ),
]


# ============================================================
# HOLLAND MAPPER CLASS
# ============================================================


class HollandMapper:
    """
    Map tên ngành → Holland RIASEC types và Career Anchors.

    Chiến lược khớp:
    1. Khớp chính xác theo major_code
    2. Khớp keyword trong tên ngành (sau khi loại bỏ dấu, lowercase)
    3. Trả về mặc định nếu không khớp được

    Cách dùng:
        mapper = HollandMapper()
        result = mapper.get_holland_types(major_code="7480201")
        result = mapper.get_holland_types(name="Kỹ thuật phần mềm")
        # → HollandResult(types=["I", "R"], anchors=[...])
    """

    def __init__(self) -> None:
        # Build lookup indexes từ HOLLAND_PROFILES
        self._code_index: dict[str, HollandProfile] = {}
        self._keyword_profiles: list[HollandProfile] = []

        for profile in HOLLAND_PROFILES:
            for code in profile.major_codes:
                self._code_index[code] = profile
            self._keyword_profiles.append(profile)

    def get_holland_types(
        self,
        major_code: str = "",
        name: str = "",
    ) -> dict[str, list[str]]:
        """
        Tra cứu Holland types và Career Anchors cho một ngành.

        Args:
            major_code: Mã ngành 7 chữ số (ưu tiên tra chính xác)
            name:       Tên ngành (dùng khi không có major_code)

        Returns:
            dict với:
                holland_types     : list[str] – VD: ["I", "R", "C"]
                career_anchor_tags: list[str] – VD: ["Technical/Functional Competence"]
        """
        profile = None

        # Bước 1: Tra theo mã ngành chính xác
        if major_code:
            profile = self._code_index.get(major_code.strip())

        # Bước 2: Tra theo tên ngành (keyword matching)
        if profile is None and name:
            profile = self._match_by_name(name)

        if profile is None:
            # Mặc định: ngành không xác định → trả về rỗng
            return {"holland_types": [], "career_anchor_tags": []}

        return {
            "holland_types": list(profile.holland_types),
            "career_anchor_tags": list(profile.career_anchors),
        }

    def _match_by_name(self, name: str) -> HollandProfile | None:
        """
        Khớp tên ngành với keyword trong HOLLAND_PROFILES.
        Trả về profile có keyword khớp đầu tiên tìm thấy.
        """
        normalized = _remove_accents_vi(name).lower()

        for profile in self._keyword_profiles:
            for keyword in profile.keywords:
                if keyword in normalized:
                    return profile

        return None


# ============================================================
# MODULE-LEVEL HELPERS
# ============================================================


def _remove_accents_vi(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để chuẩn hóa so sánh."""
    import unicodedata
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Singleton instance
_default_mapper: HollandMapper | None = None


def get_mapper() -> HollandMapper:
    """Lấy singleton instance của HollandMapper."""
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = HollandMapper()
    return _default_mapper
