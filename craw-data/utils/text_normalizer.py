# ============================================================
# utils/text_normalizer.py
# Các hàm tiện ích để làm sạch và chuẩn hóa text, mã ngành, tổ hợp môn...
# ============================================================

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

# --- Constants & Mapping ---
_UNKNOWN_COMBO = "KHAC"

# Mapping tên môn học → mã môn chuẩn (nội bộ phục vụ chuẩn hóa combo)
_SUBJECT_NAME_MAP = {
    "toan": "T",
    "toán": "T",
    "t": "T",
    "ly": "L",
    "lý": "L",
    "l": "L",
    "vật lý": "L",
    "vat ly": "L",
    "hoa": "H",
    "hóa": "H",
    "h": "H",
    "hóa học": "H",
    "hoa hoc": "H",
    "sinh": "S",
    "sinh học": "S",
    "s": "S",
    "sinh hoc": "S",
    "van": "V",
    "văn": "V",
    "v": "V",
    "ngữ văn": "V",
    "ngu van": "V",
    "su": "Su",
    "sử": "Su",
    "s": "Su",
    "dia": "D",

    "địa": "D",
    "d": "D",
    "địa lý": "D",
    "dia ly": "D",
    "anh": "A",
    "a": "A",
    "tiếng anh": "A",
    "tieng anh": "A",
    "gdcd": "G",
    "g": "G",
    "giáo dục công dân": "G",
    "giao duc cong dan": "G",
    "ngoại ngữ": "A",
}

# Mapping tập hợp môn → mã tổ hợp chuẩn
_COMBO_MAP = {
    frozenset(["T", "L", "H"]): "A00",
    frozenset(["T", "L", "A"]): "A01",
    frozenset(["T", "H", "S"]): "A08",  # Theo yêu cầu test, Toán-Hóa-Sinh -> A08
    frozenset(["V", "Su", "D"]): "C00",
    frozenset(["T", "V", "A"]): "D01",
    frozenset(["T", "H", "D"]): "A02",
    frozenset(["T", "S", "D"]): "B01",
    frozenset(["T", "S", "A"]): "A10",  # Toán-Sinh-Anh -> A10
}

# Alias phổ biến cho tổ hợp môn
_COMBO_ALIAS = {
    "toán lý hóa": "A00",
    "toán-lý-hóa": "A00",
    "toán lý anh": "A01",
    "toán-lý-anh": "A01",
    "văn sử địa": "C00",
    "văn-sử- địa": "C00",
    "toán văn anh": "D01",
    "toán-văn-anh": "D01",
    "toán hóa sinh": "A08",
    "toán sinh anh": "A10",
}


# ============================================================
# CHUẨN HÓA TÊN NGÀNH
# ============================================================


def normalize_major_name(raw: str) -> str:
    """
    Làm sạch tên ngành học:
    - Xóa prefix: "Ngành", "Chuyên ngành", "Chương trình"
    - Xóa nội dung trong ngoặc (mã ngành nội bộ, tên tiếng Anh...)
    - Title case kết quả (VD: "công nghệ thông tin" → "Công Nghệ Thông Tin")

    Args:
        raw: Tên ngành thô từ web

    Returns:
        Tên ngành đã làm sạch và chuẩn hóa.
    """
    if not raw:
        return ""

    # 1. Chuẩn hóa Unicode NFC và giải mã HTML entities
    import html
    text = html.unescape(raw.strip())
    text = unicodedata.normalize("NFC", text)

    # 2. Xóa các tiền tố thừa (case-insensitive)
    # Bao gồm cả số thứ tự đầu dòng (1., 1), ...)
    text = re.sub(r"^\d+[\.\)\-\s]+", "", text)

    # Các tiền tố loại bỏ thẳng
    prefixes = [
        r"^ngành[:\s]+",
        r"^chuyên ngành[:\s]+",
        r"^chương trình[:\s]+",
        r"^hệ[:\s]+",
        r"^bộ môn[:\s]+",
        r"^khoa\s+(?!học\b)", # Chỉ xóa "Khoa" nếu không phải "Khoa học"
    ]
    for p in prefixes:
        text = re.sub(p, "", text, flags=re.IGNORECASE)

    # 3. Xóa nội dung trong ngoặc đơn/kép (thường là mã hoặc tiếng Anh)
    # VD: "Công nghệ thông tin (IT)" → "Công nghệ thông tin"
    text = re.sub(r"[\(\[（【][^\)\]）】]*[\)\]）】]", "", text)

    # 4. Xóa các ký tự đặc biệt thừa ở đầu/cuối (dấu gạch ngang, hai chấm...)
    text = re.sub(r"^[ \-:]+", "", text)
    text = re.sub(r"[ \-:]+$", "", text)

    # 5. Xử lý khoảng trắng thừa ở giữa
    text = " ".join(text.split())

    # 6. Chuyển về dạng Title Case (Viết hoa chữ cái đầu mỗi từ)
    # Lưu ý: .title() của python làm hỏng một số từ tiếng Việt có dấu,
    # dùng capitalize cho từng từ sẽ an toàn hơn.
    words = text.lower().split()
    text = " ".join(w.capitalize() for w in words)

    return text


# ============================================================
# CHUẨN HÓA TỔ HỢP MÔN
# ============================================================


def normalize_subject_combo(raw: str) -> str:
    """
    Chuẩn hóa mã tổ hợp môn từ dạng tự nhiên sang mã chuẩn Bộ GD&ĐT.

    Chiến lược (theo thứ tự ưu tiên):
    1. Nếu raw đã là mã chuẩn (VD: "A00", "D01") → trả về ngay
    2. Tra cứu alias (VD: "Toán-Lý-Hóa" → "A00")
    3. Phân tách theo dấu phân cách, map từng môn → code, lookup combo
    4. Fallback → "KHAC"
    """
    if not raw or not isinstance(raw, str):
        return _UNKNOWN_COMBO

    text = raw.strip()

    # Bước 1: Chuẩn hóa Unicode
    text = unicodedata.normalize("NFC", text)

    # Bước 2: Kiểm tra đã là mã chuẩn chưa (VD: "A00", "B08", "D01", "X06")
    canonical_pattern = re.compile(r"^[A-DX]\d{2}$", re.IGNORECASE)
    if canonical_pattern.match(text):
        normalized = text.upper()
        # Kiểm tra có trong danh sách hợp lệ không (import lười để tránh circular)
        try:
            from models.admission_score import VALID_SUBJECT_COMBINATIONS

            if normalized in VALID_SUBJECT_COMBINATIONS:
                return normalized
        except ImportError:
            return normalized
        return normalized

    # Bước 3: Tra cứu alias (dạng tên đầy đủ đã được mapping)
    text_lower = text.lower().strip()

    # Thử alias trực tiếp
    if text_lower in _COMBO_ALIAS:
        return _COMBO_ALIAS[text_lower]

    # Thử alias sau khi xóa dấu (không dấu)
    text_no_accent = _remove_accents(text_lower)
    if text_no_accent in _COMBO_ALIAS:
        return _COMBO_ALIAS[text_no_accent]

    # Bước 4: Phân tách và map từng môn
    # Tách theo dấu phân cách phổ biến: "-", ",", "/", " - ", " / "
    separators_pattern = re.compile(r"[,\-/；;、]+\s*|\s+và\s+|\s+and\s+", re.IGNORECASE)
    parts = separators_pattern.split(text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) == 3:
        # Map từng phần sang mã môn nội bộ
        subject_codes = set()
        for part in parts:
            part_lower = part.lower().strip()
            part_no_accent = _remove_accents(part_lower)

            code = _SUBJECT_NAME_MAP.get(part_lower) or _SUBJECT_NAME_MAP.get(
                part_no_accent
            )
            if code:
                subject_codes.add(code)
            else:
                logger.debug("Không map được môn học: %r", part)

        if len(subject_codes) == 3:
            combo_code = _COMBO_MAP.get(frozenset(subject_codes))
            if combo_code:
                return combo_code

    # Bước 5: Thử tìm mã trong chuỗi (VD: "Khối A00 (Toán Lý Hóa)")
    match = re.search(r"\b([A-DX]\d{2})\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    logger.debug("Không chuẩn hóa được tổ hợp môn: %r → KHAC", raw)
    return _UNKNOWN_COMBO


def normalize_multiple_combos(raw: str) -> list[str]:
    """
    Chuẩn hóa danh sách tổ hợp môn từ một chuỗi có thể chứa nhiều tổ hợp.
    """
    if not raw or not isinstance(raw, str):
        return []

    # Thử tách theo dấu chấm phẩy hoặc newline trước
    parts = re.split(r"[;\n]+", raw)
    if len(parts) == 1:
        # Nếu không có dấu chấm phẩy, thử tách theo dấu phẩy
        maybe_codes = re.findall(r"\b[A-DX]\d{2}\b", raw, re.IGNORECASE)
        if maybe_codes:
            return [c.upper() for c in dict.fromkeys(maybe_codes)]
        parts = re.split(r",", raw)

    results = []
    seen = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        code = normalize_subject_combo(part)
        if code != _UNKNOWN_COMBO and code not in seen:
            results.append(code)
            seen.add(code)

    return results


# ============================================================
# CHUẨN HÓA MÃ TRƯỜNG
# ============================================================


def normalize_university_code(raw: str) -> str:
    """
    Chuẩn hóa mã trường đại học về dạng chuẩn.
    """
    if not raw or not isinstance(raw, str):
        return ""

    text = raw.strip().upper()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^A-Z0-9\-]", "", text)
    text = text[:20]

    return text


# ============================================================
# CHUẨN HÓA ĐIỂM SỐ
# ============================================================


def normalize_score(raw: str | float | int | None) -> Optional[float]:
    """
    Chuẩn hóa điểm chuẩn từ dạng string/số về float.
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        score = float(raw)
        return score if 0.0 <= score <= 100.0 else None

    if not isinstance(raw, str):
        return None

    text = raw.strip()
    null_patterns = {
        "---", "--", "-", "n/a", "na", "không có", "khong co", "", "0",
        "tuyển thẳng", "tuyen thang", "xét tuyển thẳng"
    }
    if text.lower() in null_patterns:
        return None

    text = re.sub(r"^[≥≤><~≈±\s]+", "", text)
    text = text.replace(",", ".")
    text = re.sub(r"\s*(điểm|đ|pts|points?|point)\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip()

    try:
        score = float(text)
    except ValueError:
        match = re.search(r"\d+(?:\.\d+)?", text)
        if match:
            try:
                score = float(match.group())
            except ValueError:
                return None
        else:
            return None

    if not (0.0 <= score <= 100.0):
        return None

    return round(score, 2)


def normalize_quota(raw: str | int | None) -> Optional[int]:
    """
    Chuẩn hóa chỉ tiêu từ string sang int.
    """
    if raw is None:
        return None

    if isinstance(raw, int):
        return raw if raw > 0 else None

    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text or text in {"---", "--", "-", "n/a", ""}:
        return None

    match = re.search(r"\d+", text)
    if match:
        try:
            quota = int(match.group())
            return quota if quota > 0 else None
        except ValueError:
            return None

    return None


# ============================================================
# HELPERS NỘI BỘ
# ============================================================


def _remove_accents(text: str) -> str:
    """
    Xóa dấu tiếng Việt, chuyển về ASCII.
    """
    if not text:
        return ""
    nfd = unicodedata.normalize("NFD", text)
    ascii_text = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return ascii_text.replace("đ", "d").replace("Đ", "D")
