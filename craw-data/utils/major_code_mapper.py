# ============================================================
# utils/major_code_mapper.py
# Ánh xạ tên ngành học thô (raw) → mã ngành chuẩn 7 chữ số (Bộ GD&ĐT)
#
# Mục đích:
#   Sau khi spider crawl về tên ngành dạng tự nhiên (VD: "Kỹ thuật phần mềm",
#   "CNTT", "Software Engineering"), NormalizationPipeline dùng mapper này
#   để chuyển về mã chuẩn trước khi resolve UUID trong DB.
#
# Chiến lược mapping (theo thứ tự ưu tiên):
#   1. Exact match (tên đã chuẩn hóa)
#   2. Alias / viết tắt thường gặp
#   3. Fuzzy match (difflib – tỷ lệ giống nhau >= 0.85)
#   4. Trả về None → NormalizationPipeline sẽ fallback sang DB search
# ============================================================

from __future__ import annotations

import logging
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# BẢNG MAPPING CHÍNH
# key   : tên ngành đã chuẩn hóa (lower, NFC, không có prefix thừa)
# value : mã ngành 7 chữ số theo danh mục Bộ GD&ĐT
#
# Tham chiếu: Thông tư 24/2017/TT-BGDĐT và các cập nhật sau
# ============================================================

_MAJOR_CODE_MAP: dict[str, str] = {
    # ──────────────────────────────────────────────────────────
    # NHÓM I – KHOA HỌC MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN (748x)
    # ──────────────────────────────────────────────────────────
    "công nghệ thông tin": "7480201",
    "cntt": "7480201",
    "information technology": "7480201",
    "it": "7480201",
    "kỹ thuật phần mềm": "7480103",
    "ktpm": "7480103",
    "software engineering": "7480103",
    "khoa học máy tính": "7480101",
    "computer science": "7480101",
    "khmt": "7480101",
    "mạng máy tính và truyền thông dữ liệu": "7480102",
    "mạng máy tính": "7480102",
    "truyền thông dữ liệu": "7480102",
    "computer networks": "7480102",
    "hệ thống thông tin": "7480104",
    "httt": "7480104",
    "information systems": "7480104",
    "an toàn thông tin": "7480202",
    "attt": "7480202",
    "information security": "7480202",
    "trí tuệ nhân tạo": "7480107",
    "ttnt": "7480107",
    "artificial intelligence": "7480107",
    "ai": "7480107",
    "khoa học dữ liệu": "7480108",
    "data science": "7480108",
    "kỹ thuật máy tính": "7480106",
    "computer engineering": "7480106",
    "công nghệ thông tin (việt nhật)": "7480201",
    "công nghệ thông tin (chất lượng cao)": "7480201",
    "công nghệ thông tin (tiên tiến)": "7480201",
    "thương mại điện tử": "7340122",
    "tmđt": "7340122",
    "e-commerce": "7340122",
    # ──────────────────────────────────────────────────────────
    # NHÓM II – KỸ THUẬT (751x)
    # ──────────────────────────────────────────────────────────
    "kỹ thuật cơ khí": "7520103",
    "cơ khí": "7520103",
    "mechanical engineering": "7520103",
    "kỹ thuật điện": "7520201",
    "điện": "7520201",
    "electrical engineering": "7520201",
    "kỹ thuật điện tử viễn thông": "7520207",
    "điện tử viễn thông": "7520207",
    "electronics and telecommunications": "7520207",
    "kỹ thuật điều khiển và tự động hóa": "7520216",
    "tự động hóa": "7520216",
    "automation engineering": "7520216",
    "kỹ thuật xây dựng": "7580201",
    "xây dựng": "7580201",
    "civil engineering": "7580201",
    "kỹ thuật hóa học": "7520301",
    "hóa học": "7520301",
    "chemical engineering": "7520301",
    "kỹ thuật môi trường": "7520320",
    "môi trường": "7520320",
    "environmental engineering": "7520320",
    "kỹ thuật cơ điện tử": "7520114",
    "cơ điện tử": "7520114",
    "mechatronics": "7520114",
    "kỹ thuật ô tô": "7520130",
    "ô tô": "7520130",
    "automotive engineering": "7520130",
    "kỹ thuật hàng không": "7520102",
    "hàng không": "7520102",
    "aerospace engineering": "7520102",
    "kỹ thuật điện – điện tử": "7520201",
    "kỹ thuật điện - điện tử": "7520201",
    "kỹ thuật vật liệu": "7520309",
    "vật liệu": "7520309",
    "materials engineering": "7520309",
    "kỹ thuật dầu khí": "7520604",
    "dầu khí": "7520604",
    "petroleum engineering": "7520604",
    "kỹ thuật địa chất": "7520501",
    "địa chất": "7520501",
    "kỹ thuật trắc địa - bản đồ": "7520503",
    "trắc địa bản đồ": "7520503",
    "kỹ thuật in": "7520171",
    "in": "7520171",
    "kỹ thuật thực phẩm": "7540101",
    "công nghệ thực phẩm": "7540101",
    "food technology": "7540101",
    "công nghệ sinh học": "7420201",
    "cnsh": "7420201",
    "biotechnology": "7420201",
    # ──────────────────────────────────────────────────────────
    # NHÓM III – KINH TẾ VÀ QUẢN TRỊ (734x)
    # ──────────────────────────────────────────────────────────
    "quản trị kinh doanh": "7340101",
    "qtkd": "7340101",
    "business administration": "7340101",
    "mba": "7340101",
    "kinh tế": "7310101",
    "economics": "7310101",
    "tài chính ngân hàng": "7340201",
    "tài chính - ngân hàng": "7340201",
    "finance and banking": "7340201",
    "kế toán": "7340301",
    "accounting": "7340301",
    "kiểm toán": "7340302",
    "auditing": "7340302",
    "marketing": "7340115",
    "quản trị marketing": "7340115",
    "kinh tế quốc tế": "7310106",
    "international economics": "7310106",
    "thương mại": "7340121",
    "kinh doanh thương mại": "7340121",
    "commerce": "7340121",
    "logistics và quản lý chuỗi cung ứng": "7510605",
    "logistics": "7510605",
    "supply chain management": "7510605",
    "quản lý nhà nước": "7340403",
    "hành chính công": "7340403",
    "quản trị nhân lực": "7340404",
    "human resource management": "7340404",
    "hrm": "7340404",
    "bất động sản": "7340116",
    "real estate": "7340116",
    "đầu tư tài chính": "7340201",
    "ngân hàng": "7340201",
    "bảo hiểm": "7340204",
    "insurance": "7340204",
    "kinh tế phát triển": "7310104",
    "hệ thống thông tin quản lý": "7340405",
    "management information systems": "7340405",
    "mis": "7340405",
    "quản trị dịch vụ du lịch và lữ hành": "7810103",
    "du lịch": "7810101",
    "tourism": "7810101",
    "quản trị khách sạn": "7810201",
    "khách sạn": "7810201",
    "hotel management": "7810201",
    "quản trị nhà hàng và dịch vụ ăn uống": "7810202",
    # ──────────────────────────────────────────────────────────
    # NHÓM IV – NGÔN NGỮ VÀ NHÂN VĂN (722x)
    # ──────────────────────────────────────────────────────────
    "ngôn ngữ anh": "7220201",
    "tiếng anh": "7220201",
    "english language": "7220201",
    "ngôn ngữ trung quốc": "7220204",
    "tiếng trung": "7220204",
    "chinese language": "7220204",
    "ngôn ngữ nhật": "7220209",
    "tiếng nhật": "7220209",
    "japanese language": "7220209",
    "ngôn ngữ hàn quốc": "7220210",
    "tiếng hàn": "7220210",
    "korean language": "7220210",
    "ngôn ngữ pháp": "7220202",
    "tiếng pháp": "7220202",
    "french language": "7220202",
    "ngôn ngữ nga": "7220203",
    "tiếng nga": "7220203",
    "russian language": "7220203",
    "ngôn ngữ đức": "7220205",
    "tiếng đức": "7220205",
    "german language": "7220205",
    "ngôn ngữ ý": "7220206",
    "ngôn ngữ tây ban nha": "7220207",
    "tiếng tây ban nha": "7220207",
    "ngôn ngữ học": "7229020",
    "linguistics": "7229020",
    "văn học": "7229030",
    "literature": "7229030",
    "lịch sử": "7229010",
    "history": "7229010",
    "triết học": "7229001",
    "philosophy": "7229001",
    "đông phương học": "7229040",
    "quan hệ quốc tế": "7310206",
    "international relations": "7310206",
    # ──────────────────────────────────────────────────────────
    # NHÓM V – Y DƯỢC (720x)
    # ──────────────────────────────────────────────────────────
    "y khoa": "7720101",
    "bác sĩ đa khoa": "7720101",
    "general medicine": "7720101",
    "y học cổ truyền": "7720115",
    "đông y": "7720115",
    "traditional medicine": "7720115",
    "dược học": "7720201",
    "pharmacy": "7720201",
    "điều dưỡng": "7720301",
    "nursing": "7720301",
    "răng hàm mặt": "7720501",
    "nha khoa": "7720501",
    "dentistry": "7720501",
    "y tế công cộng": "7720701",
    "public health": "7720701",
    "kỹ thuật xét nghiệm y học": "7720601",
    "xét nghiệm y học": "7720601",
    # ──────────────────────────────────────────────────────────
    # NHÓM VI – SƯ PHẠM (714x)
    # ──────────────────────────────────────────────────────────
    "sư phạm toán học": "7140209",
    "sư phạm toán": "7140209",
    "sư phạm vật lý": "7140211",
    "sư phạm hóa học": "7140212",
    "sư phạm sinh học": "7140213",
    "sư phạm ngữ văn": "7140217",
    "sư phạm lịch sử": "7140218",
    "sư phạm địa lý": "7140219",
    "sư phạm tiếng anh": "7140231",
    "sư phạm tin học": "7140210",
    "giáo dục mầm non": "7140201",
    "giáo dục tiểu học": "7140202",
    "giáo dục thể chất": "7140206",
    "giáo dục đặc biệt": "7140120",
    # ──────────────────────────────────────────────────────────
    # NHÓM VII – LUẬT VÀ XÃ HỘI (738x)
    # ──────────────────────────────────────────────────────────
    "luật": "7380101",
    "law": "7380101",
    "luật kinh tế": "7380107",
    "business law": "7380107",
    "luật quốc tế": "7380108",
    "international law": "7380108",
    "xã hội học": "7310301",
    "sociology": "7310301",
    "tâm lý học": "7310401",
    "psychology": "7310401",
    "công tác xã hội": "7760101",
    "social work": "7760101",
    "nhân học": "7310302",
    "đông nam á học": "7310630",
    "việt nam học": "7310630",
    # ──────────────────────────────────────────────────────────
    # NHÓM VIII – KIẾN TRÚC VÀ THIẾT KẾ (758x)
    # ──────────────────────────────────────────────────────────
    "kiến trúc": "7580101",
    "architecture": "7580101",
    "quy hoạch vùng và đô thị": "7580105",
    "thiết kế đồ họa": "7210403",
    "graphic design": "7210403",
    "thiết kế thời trang": "7210404",
    "fashion design": "7210404",
    "thiết kế công nghiệp": "7210402",
    "industrial design": "7210402",
    "thiết kế nội thất": "7580108",
    "interior design": "7580108",
    "mỹ thuật": "7210101",
    "fine arts": "7210101",
    "hội họa": "7210102",
    "điêu khắc": "7210103",
    # ──────────────────────────────────────────────────────────
    # NHÓM IX – NÔNG LÂM THỦY SẢN (762x)
    # ──────────────────────────────────────────────────────────
    "nông nghiệp": "7620101",
    "agriculture": "7620101",
    "lâm nghiệp": "7620201",
    "forestry": "7620201",
    "thủy sản": "7620301",
    "fisheries": "7620301",
    "chăn nuôi": "7620105",
    "thú y": "7640101",
    "veterinary medicine": "7640101",
    "khoa học đất": "7620103",
    "bảo vệ thực vật": "7620112",
    "công nghệ rau hoa quả và cảnh quan": "7549062",
    # ──────────────────────────────────────────────────────────
    # NHÓM X – BÁO CHÍ VÀ TRUYỀN THÔNG (732x)
    # ──────────────────────────────────────────────────────────
    "báo chí": "7320101",
    "journalism": "7320101",
    "truyền thông đa phương tiện": "7320104",
    "multimedia": "7320104",
    "quan hệ công chúng": "7320107",
    "public relations": "7320107",
    "pr": "7320107",
    "xuất bản": "7320201",
    "publishing": "7320201",
    "phát thanh truyền hình": "7320105",
    # ──────────────────────────────────────────────────────────
    # NHÓM XI – NGHỆ THUẬT VÀ ÂM NHẠC (721x)
    # ──────────────────────────────────────────────────────────
    "âm nhạc": "7210201",
    "music": "7210201",
    "điện ảnh": "7210221",
    "film": "7210221",
    "sân khấu": "7210231",
    "dance": "7210241",
    "múa": "7210241",
    # ──────────────────────────────────────────────────────────
    # NHÓM XII – KHOA HỌC TỰ NHIÊN (744x)
    # ──────────────────────────────────────────────────────────
    "toán học": "7460101",
    "mathematics": "7460101",
    "toán ứng dụng": "7460112",
    "applied mathematics": "7460112",
    "vật lý học": "7440102",
    "physics": "7440102",
    "hóa học (khtn)": "7440112",
    "sinh học (khtn)": "7420101",
    "biology": "7420101",
    "địa lý tự nhiên": "7440217",
    "khoa học môi trường": "7440301",
    "environmental science": "7440301",
    "hải dương học": "7440228",
    "khí tượng thủy văn": "7440224",
    # ──────────────────────────────────────────────────────────
    # NHÓM XIII – TÀI CHÍNH VÀ BẢO HIỂM (734x tiếp theo)
    # ──────────────────────────────────────────────────────────
    "tài chính": "7340201",
    "finance": "7340201",
    "ngân hàng thương mại": "7340201",
    "phân tích tài chính": "7340201",
    "chứng khoán": "7340201",
    # ──────────────────────────────────────────────────────────
    # NHÓM XIV – QUẢN LÝ VÀ DỊCH VỤ (734x, 810x)
    # ──────────────────────────────────────────────────────────
    "quản lý công nghiệp": "7510601",
    "industrial management": "7510601",
    "kỹ thuật công nghiệp": "7510601",
    "quản lý xây dựng": "7580302",
    "quản lý đô thị và công trình": "7580301",
    "quản lý tài nguyên và môi trường": "7850101",
    "resource and environment management": "7850101",
    "quản lý văn hóa": "7229042",
    "bảo tàng học": "7229043",
    "quản lý giáo dục": "7140114",
    "education management": "7140114",
    "quản lý thể dục thể thao": "7810302",
    "sports management": "7810302",
    "thể dục thể thao": "7810302",
}

# ──────────────────────────────────────────────────────────
# BẢNG ALIAS – Tên viết tắt và biến thể phổ biến
# (mapping từ alias → tên chuẩn trong _MAJOR_CODE_MAP)
# ──────────────────────────────────────────────────────────
_ALIAS_MAP: dict[str, str] = {
    # CNTT và các chuyên ngành
    "cntt": "công nghệ thông tin",
    "it": "công nghệ thông tin",
    "ktpm": "kỹ thuật phần mềm",
    "khmt": "khoa học máy tính",
    "httt": "hệ thống thông tin",
    "attt": "an toàn thông tin",
    "ttnt": "trí tuệ nhân tạo",
    "cnsh": "công nghệ sinh học",
    "mis": "hệ thống thông tin quản lý",
    # Kỹ thuật
    "ck": "kỹ thuật cơ khí",
    "cdt": "kỹ thuật cơ điện tử",
    "dtvt": "kỹ thuật điện tử viễn thông",
    # Kinh tế
    "qtkd": "quản trị kinh doanh",
    "mba": "quản trị kinh doanh",
    "tmdt": "thương mại điện tử",
    "tmđt": "thương mại điện tử",
    "hrm": "quản trị nhân lực",
    "pr": "quan hệ công chúng",
    # Y dược
    "y đa khoa": "y khoa",
    "bs đa khoa": "y khoa",
    # Viết tắt tên trường/chuyên ngành
    "se": "kỹ thuật phần mềm",
    "cs": "khoa học máy tính",
    "is": "an toàn thông tin",
    "ai": "trí tuệ nhân tạo",
    "ds": "khoa học dữ liệu",
    "ce": "kỹ thuật máy tính",
}

# Ngưỡng tối thiểu cho fuzzy match (0.0 – 1.0)
_FUZZY_THRESHOLD = 0.82


class MajorCodeMapper:
    """
    Mapper từ tên ngành thô (raw) → mã ngành 7 chữ số chuẩn Bộ GD&ĐT.

    Sử dụng trong NormalizationPipeline trước khi resolve UUID từ DB.

    Ví dụ sử dụng:
        mapper = MajorCodeMapper()
        code = mapper.get_code("Kỹ thuật phần mềm (KTPM)")
        # → "7480103"

        code = mapper.get_code("Cntt")
        # → "7480201"

        code = mapper.get_code("Software Engineering")
        # → "7480103"

        code = mapper.get_code("xyz không tồn tại")
        # → None
    """

    def __init__(self, custom_map: dict[str, str] | None = None) -> None:
        """
        Khởi tạo mapper.

        Args:
            custom_map: Dict tùy chọn để override/bổ sung mapping mặc định.
                        Key: tên ngành (sẽ được chuẩn hóa), Value: mã ngành.
        """
        # Build lookup table: tên đã chuẩn hóa → major_code
        self._lookup: dict[str, str] = {}

        # Nạp bảng chính
        for name, code in _MAJOR_CODE_MAP.items():
            self._lookup[_normalize_key(name)] = code

        # Nạp alias (resolve alias → tên chuẩn → code)
        for alias, canonical_name in _ALIAS_MAP.items():
            canonical_key = _normalize_key(canonical_name)
            if canonical_key in self._lookup:
                alias_key = _normalize_key(alias)
                self._lookup[alias_key] = self._lookup[canonical_key]

        # Nạp custom map (override nếu có)
        if custom_map:
            for name, code in custom_map.items():
                self._lookup[_normalize_key(name)] = code.strip()

        # Cache key list để dùng cho fuzzy match
        self._keys: list[str] = list(self._lookup.keys())

        logger.debug("MajorCodeMapper khởi tạo với %d entries.", len(self._lookup))

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def get_code(self, major_name_raw: str) -> Optional[str]:
        """
        Resolve tên ngành thô → mã ngành 7 chữ số.

        Chiến lược (theo thứ tự ưu tiên):
        1. Exact match sau khi chuẩn hóa key
        2. Exact match sau khi bỏ dấu (non-accent key)
        3. Fuzzy match (SequenceMatcher ratio >= _FUZZY_THRESHOLD)
        4. Trả về None

        Args:
            major_name_raw: Tên ngành thô từ HTML

        Returns:
            Mã ngành 7 chữ số (VD: "7480201"), hoặc None nếu không match.
        """
        if not major_name_raw or not isinstance(major_name_raw, str):
            return None

        # Bước 1: Clean và normalize key
        cleaned = _clean_raw_name(major_name_raw)
        if not cleaned:
            return None

        key = _normalize_key(cleaned)

        # Bước 1a: Exact match
        if key in self._lookup:
            logger.debug("Exact match: %r → %s", major_name_raw, self._lookup[key])
            return self._lookup[key]

        # Bước 1b: Thử sau khi xóa dấu
        key_no_accent = _remove_accents(key)
        lookup_no_accent = {_remove_accents(k): v for k, v in self._lookup.items()}
        if key_no_accent in lookup_no_accent:
            result = lookup_no_accent[key_no_accent]
            logger.debug("No-accent match: %r → %s", major_name_raw, result)
            return result

        # Bước 2: Thử bỏ nội dung trong ngoặc rồi match lại
        stripped = re.sub(r"\s*[\(\[（【][^\)\]）】]*[\)\]）】]", "", cleaned).strip()
        if stripped != cleaned:
            stripped_key = _normalize_key(stripped)
            if stripped_key in self._lookup:
                result = self._lookup[stripped_key]
                logger.debug("Match sau bỏ ngoặc: %r → %s", major_name_raw, result)
                return result

        # Bước 3: Fuzzy match
        result = self._fuzzy_match(key)
        if result:
            logger.debug("Fuzzy match: %r → %s", major_name_raw, result)
            return result

        logger.debug("Không tìm được mã ngành cho: %r", major_name_raw)
        return None

    def get_code_batch(self, names: list[str]) -> dict[str, Optional[str]]:
        """
        Resolve danh sách tên ngành cùng lúc.

        Args:
            names: Danh sách tên ngành thô

        Returns:
            Dict {tên_thô → mã_ngành} (mã_ngành có thể là None nếu không resolve được)
        """
        return {name: self.get_code(name) for name in names}

    def add_mapping(self, name: str, code: str) -> None:
        """
        Thêm mapping mới vào runtime (dùng để bổ sung từ DB seed).

        Args:
            name: Tên ngành (sẽ được chuẩn hóa tự động)
            code: Mã ngành 7 chữ số
        """
        key = _normalize_key(name)
        self._lookup[key] = code.strip()
        if key not in self._keys:
            self._keys.append(key)

    def _fuzzy_match(self, key: str) -> Optional[str]:
        """
        Tìm kiếm fuzzy match trong lookup table.

        Dùng SequenceMatcher để tính tỷ lệ giống nhau giữa key
        và các key trong lookup. Trả về mã ngành của key tốt nhất
        nếu tỷ lệ >= _FUZZY_THRESHOLD.

        Args:
            key: Key đã được chuẩn hóa (lowercase, no extra spaces)

        Returns:
            Mã ngành nếu tìm được, None nếu không.
        """
        best_ratio = 0.0
        best_code: Optional[str] = None

        for candidate_key in self._keys:
            ratio = SequenceMatcher(None, key, candidate_key).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_code = self._lookup[candidate_key]

        if best_ratio >= _FUZZY_THRESHOLD:
            return best_code

        return None


# ============================================================
# MODULE-LEVEL HELPER FUNCTIONS
# ============================================================


def _clean_raw_name(raw: str) -> str:
    """
    Làm sạch tên ngành thô trước khi normalize key.

    - Strip khoảng trắng
    - Chuẩn hóa Unicode NFC
    - Xóa prefix thừa (Ngành:, Chuyên ngành:, ...)
    - Xóa nội dung trong ngoặc ở cuối
    - Xóa số thứ tự đầu dòng
    """
    import unicodedata as _unicodedata

    text = raw.strip()
    text = _unicodedata.normalize("NFC", text)

    # Xóa HTML entities
    text = re.sub(r"&[a-zA-Z]+;", " ", text)

    # Xóa nội dung trong ngoặc ở cuối
    text = re.sub(r"\s*[\(\[（【][^\)\]）】]*[\)\]）】]\s*$", "", text)

    # Xóa prefix thừa
    prefixes_pattern = (
        r"^("
        r"ngành\s*[:\-]?\s*|"
        r"chuyên ngành\s*[:\-]?\s*|"
        r"bộ môn\s*[:\-]?\s*|"
        r"khoa\s*[:\-]?\s*|"
        r"chương trình\s*[:\-]?\s*|"
        r"hệ\s*[:\-]?\s*"
        r")"
    )
    text = re.sub(prefixes_pattern, "", text, flags=re.IGNORECASE)

    # Xóa số thứ tự
    text = re.sub(r"^\d+[\.\)]\s*", "", text)

    # Chuẩn hóa khoảng trắng
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _normalize_key(text: str) -> str:
    """
    Chuẩn hóa một chuỗi thành lookup key chuẩn.

    Các bước:
    1. Lowercase
    2. Strip khoảng trắng
    3. Chuẩn hóa Unicode NFC
    4. Chuẩn hóa khoảng trắng nội dung (nhiều space → 1 space)

    Args:
        text: Chuỗi đầu vào

    Returns:
        Key đã chuẩn hóa
    """
    import unicodedata as _unicodedata

    if not text:
        return ""

    key = text.lower().strip()
    key = _unicodedata.normalize("NFC", key)
    key = re.sub(r"\s+", " ", key)
    return key


def _remove_accents(text: str) -> str:
    """
    Xóa dấu tiếng Việt, chuyển về dạng không dấu.

    VD: "kỹ thuật phần mềm" → "ky thuat phan mem"

    Args:
        text: Chuỗi tiếng Việt có dấu

    Returns:
        Chuỗi không dấu (ASCII)
    """
    import unicodedata as _unicodedata

    nfd = _unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if _unicodedata.category(ch) != "Mn")
