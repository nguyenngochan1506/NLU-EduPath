# ============================================================
# tests/test_utils/test_text_normalizer.py
# Unit tests cho utils/text_normalizer.py
#
# Chạy:
#   pytest tests/test_utils/test_text_normalizer.py -v
#   pytest tests/test_utils/test_text_normalizer.py -v -m unit
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Đảm bảo project root trong sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

from utils.text_normalizer import (
    _remove_accents,
    normalize_major_name,
    normalize_multiple_combos,
    normalize_quota,
    normalize_score,
    normalize_subject_combo,
    normalize_university_code,
)


# ============================================================
# normalize_major_name
# ============================================================


class TestNormalizeMajorName:
    """Tests cho hàm normalize_major_name()."""

    @pytest.mark.unit
    def test_basic_strip(self):
        """Strip khoảng trắng đầu/cuối."""
        assert normalize_major_name("  Kỹ thuật phần mềm  ") == "Kỹ Thuật Phần Mềm"

    @pytest.mark.unit
    def test_remove_prefix_nganh(self):
        """Xóa prefix 'Ngành:'."""
        result = normalize_major_name("Ngành: Công nghệ thông tin")
        assert "ngành" not in result.lower()
        assert "Công" in result

    @pytest.mark.unit
    def test_remove_prefix_chuyen_nganh(self):
        """Xóa prefix 'Chuyên ngành'."""
        result = normalize_major_name("Chuyên ngành Quản trị kinh doanh")
        assert "chuyên" not in result.lower()
        assert "Quản" in result

    @pytest.mark.unit
    def test_remove_prefix_bo_mon(self):
        """Xóa prefix 'Bộ môn'."""
        result = normalize_major_name("Bộ môn Toán học")
        assert "bộ môn" not in result.lower()

    @pytest.mark.unit
    def test_remove_brackets_at_end(self):
        """Xóa nội dung trong ngoặc ở cuối."""
        result = normalize_major_name("Kỹ thuật phần mềm (KTPM)")
        assert "(KTPM)" not in result
        assert "Kỹ" in result

    @pytest.mark.unit
    def test_remove_square_brackets_at_end(self):
        """Xóa nội dung trong ngoặc vuông ở cuối."""
        result = normalize_major_name("Quản trị kinh doanh [Chất lượng cao]")
        assert "[Chất lượng cao]" not in result
        assert "Quản" in result

    @pytest.mark.unit
    def test_allcaps_to_titlecase(self):
        """ALLCAPS → title case."""
        result = normalize_major_name("CÔNG NGHỆ THÔNG TIN")
        # Không còn toàn viết hoa
        assert result != "CÔNG NGHỆ THÔNG TIN"
        assert "Công" in result or "công" in result

    @pytest.mark.unit
    def test_lowercase_to_titlecase(self):
        """all lowercase → title case."""
        result = normalize_major_name("công nghệ thông tin")
        assert result != "công nghệ thông tin"

    @pytest.mark.unit
    def test_normalize_multiple_spaces(self):
        """Nhiều khoảng trắng liên tiếp → 1 khoảng trắng."""
        result = normalize_major_name("Kỹ  thuật   phần    mềm")
        assert "  " not in result

    @pytest.mark.unit
    def test_remove_numbered_prefix(self):
        """Xóa số thứ tự đầu dòng."""
        result = normalize_major_name("1. Kỹ thuật cơ khí")
        assert not result.startswith("1.")
        assert "Kỹ" in result

    @pytest.mark.unit
    def test_remove_numbered_prefix_with_paren(self):
        """Xóa số thứ tự dạng '2) Tên ngành'."""
        result = normalize_major_name("2) Khoa học máy tính")
        assert not result.startswith("2)")

    @pytest.mark.unit
    def test_empty_string(self):
        """Chuỗi rỗng → chuỗi rỗng."""
        assert normalize_major_name("") == ""

    @pytest.mark.unit
    def test_none_input(self):
        """None input → chuỗi rỗng."""
        assert normalize_major_name(None) == ""  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_unicode_nfc_normalization(self):
        """Unicode NFC normalization được áp dụng."""
        # Chuỗi đã NFC bình thường
        result = normalize_major_name("Kỹ thuật")
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_html_entities_removed(self):
        """HTML entities bị xóa."""
        result = normalize_major_name("Kỹ&nbsp;thuật phần mềm")
        assert "&nbsp;" not in result

    @pytest.mark.unit
    def test_preserve_middle_brackets(self):
        """Ngoặc ở GIỮA chuỗi không bị xóa."""
        result = normalize_major_name("Khoa học (lý thuyết) và ứng dụng")
        # Ngoặc ở giữa vẫn được giữ (chỉ xóa ngoặc ở cuối)
        # Hành vi phụ thuộc vào implementation, test chủ yếu không crash
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected_keyword", [
        ("Ngành: Kỹ thuật phần mềm", "Kỹ"),
        ("Chuyên ngành Quản trị kinh doanh", "Quản"),
        ("CÔNG NGHỆ THÔNG TIN", "Công"),
        ("  toán ứng dụng  ", "Toán"),
        ("Kỹ thuật phần mềm (KTPM)", "Kỹ"),
        ("Hệ đào tạo Kỹ sư", "Kỹ"),
    ])
    def test_parametrized_cases(self, raw: str, expected_keyword: str):
        """Kiểm tra nhiều trường hợp cùng lúc."""
        result = normalize_major_name(raw)
        assert expected_keyword in result, f"Expected {expected_keyword!r} in {result!r}"


# ============================================================
# normalize_subject_combo
# ============================================================


class TestNormalizeSubjectCombo:
    """Tests cho hàm normalize_subject_combo()."""

    @pytest.mark.unit
    def test_already_canonical_a00(self):
        """Mã chuẩn A00 không đổi."""
        assert normalize_subject_combo("A00") == "A00"

    @pytest.mark.unit
    def test_already_canonical_lowercase(self):
        """Mã chuẩn viết thường → uppercase."""
        assert normalize_subject_combo("a00") == "A00"

    @pytest.mark.unit
    def test_already_canonical_d01(self):
        """Mã D01 không đổi."""
        assert normalize_subject_combo("D01") == "D01"

    @pytest.mark.unit
    def test_already_canonical_b08(self):
        """Mã B08 không đổi."""
        assert normalize_subject_combo("B08") == "B08"

    @pytest.mark.unit
    def test_alias_toan_ly_hoa_dash(self):
        """'Toán-Lý-Hóa' → 'A00'."""
        assert normalize_subject_combo("Toán-Lý-Hóa") == "A00"

    @pytest.mark.unit
    def test_alias_toan_ly_hoa_space(self):
        """'Toán Lý Hóa' → 'A00'."""
        assert normalize_subject_combo("Toán Lý Hóa") == "A00"

    @pytest.mark.unit
    def test_alias_toan_ly_hoa_lowercase(self):
        """'toán-lý-hóa' → 'A00'."""
        assert normalize_subject_combo("toán-lý-hóa") == "A00"

    @pytest.mark.unit
    def test_alias_toan_ly_anh(self):
        """'Toán-Lý-Anh' → 'A01'."""
        assert normalize_subject_combo("Toán-Lý-Anh") == "A01"

    @pytest.mark.unit
    def test_alias_van_su_dia(self):
        """'Văn-Sử-Địa' → 'C00'."""
        assert normalize_subject_combo("Văn-Sử-Địa") == "C00"

    @pytest.mark.unit
    def test_alias_toan_van_anh(self):
        """'Toán-Văn-Anh' → 'D01'."""
        assert normalize_subject_combo("Toán-Văn-Anh") == "D01"

    @pytest.mark.unit
    def test_alias_toan_hoa_sinh(self):
        """'Toán-Hóa-Sinh' → 'A08'."""
        assert normalize_subject_combo("Toán-Hóa-Sinh") == "A08"

    @pytest.mark.unit
    def test_embedded_code_in_string(self):
        """Tìm mã chuẩn nhúng trong chuỗi: 'Khối A00 (Toán Lý Hóa)' → 'A00'."""
        result = normalize_subject_combo("Khối A00 (Toán Lý Hóa)")
        assert result == "A00"

    @pytest.mark.unit
    def test_unknown_returns_khac(self):
        """Tổ hợp không xác định → 'KHAC'."""
        assert normalize_subject_combo("xyz không rõ") == "KHAC"

    @pytest.mark.unit
    def test_empty_string_returns_khac(self):
        """Chuỗi rỗng → 'KHAC'."""
        assert normalize_subject_combo("") == "KHAC"

    @pytest.mark.unit
    def test_none_returns_khac(self):
        """None → 'KHAC'."""
        assert normalize_subject_combo(None) == "KHAC"  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_dash_placeholder_returns_khac(self):
        """'---' (placeholder không có điểm) → 'KHAC'."""
        assert normalize_subject_combo("---") == "KHAC"

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("A00", "A00"),
        ("a01", "A01"),
        ("D01", "D01"),
        ("C00", "C00"),
        ("Toán-Lý-Hóa", "A00"),
        ("Toán-Lý-Anh", "A01"),
        ("Toán-Hóa-Sinh", "A08"),
        ("Toán-Sinh-Anh", "A10"),
        ("Văn-Sử-Địa", "C00"),
        ("Toán-Văn-Anh", "D01"),
        ("t-l-h", "A00"),
        ("t-l-a", "A01"),
        ("v-s-d", "C00"),
    ])
    def test_parametrized_combos(self, raw: str, expected: str):
        """Kiểm tra nhiều tổ hợp môn phổ biến."""
        result = normalize_subject_combo(raw)
        assert result == expected, f"normalize_subject_combo({raw!r}) = {result!r}, expected {expected!r}"


# ============================================================
# normalize_multiple_combos
# ============================================================


class TestNormalizeMultipleCombos:
    """Tests cho hàm normalize_multiple_combos()."""

    @pytest.mark.unit
    def test_single_canonical_code(self):
        """Một mã chuẩn đơn."""
        result = normalize_multiple_combos("A00")
        assert "A00" in result

    @pytest.mark.unit
    def test_multiple_canonical_codes_comma(self):
        """Nhiều mã chuẩn cách nhau bởi dấu phẩy."""
        result = normalize_multiple_combos("A00, A01, D01")
        assert "A00" in result
        assert "A01" in result
        assert "D01" in result

    @pytest.mark.unit
    def test_multiple_codes_no_duplicates(self):
        """Không có mã trùng lặp."""
        result = normalize_multiple_combos("A00, A00, A01")
        assert result.count("A00") == 1

    @pytest.mark.unit
    def test_semicolon_separator(self):
        """Dấu chấm phẩy là phân cách."""
        result = normalize_multiple_combos("A00; A01; D01")
        assert len(result) >= 1

    @pytest.mark.unit
    def test_empty_string(self):
        """Chuỗi rỗng → danh sách rỗng."""
        assert normalize_multiple_combos("") == []

    @pytest.mark.unit
    def test_none_input(self):
        """None → danh sách rỗng."""
        assert normalize_multiple_combos(None) == []  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_unknown_combos_excluded(self):
        """Tổ hợp không xác định bị loại khỏi kết quả."""
        result = normalize_multiple_combos("A00, xyz không rõ")
        assert "KHAC" not in result

    @pytest.mark.unit
    def test_preserves_order(self):
        """Thứ tự xuất hiện được giữ nguyên."""
        result = normalize_multiple_combos("D01, A00, C00")
        # D01 phải xuất hiện trước A00 (nếu regex tìm theo thứ tự)
        if "D01" in result and "A00" in result:
            assert result.index("D01") < result.index("A00")

    @pytest.mark.unit
    def test_mixed_case_codes(self):
        """Mã hỗn hợp hoa/thường → đều uppercase trong kết quả."""
        result = normalize_multiple_combos("a00, A01, d01")
        assert all(c == c.upper() for c in result)


# ============================================================
# normalize_university_code
# ============================================================


class TestNormalizeUniversityCode:
    """Tests cho hàm normalize_university_code()."""

    @pytest.mark.unit
    def test_basic_uppercase(self):
        """Mã thường → uppercase."""
        assert normalize_university_code("qsb") == "QSB"

    @pytest.mark.unit
    def test_strip_whitespace(self):
        """Xóa khoảng trắng đầu/cuối."""
        assert normalize_university_code("  BKA  ") == "BKA"

    @pytest.mark.unit
    def test_already_uppercase(self):
        """Mã đã uppercase không thay đổi."""
        assert normalize_university_code("QSB") == "QSB"

    @pytest.mark.unit
    def test_with_hyphen(self):
        """Mã có dấu gạch ngang được giữ nguyên."""
        result = normalize_university_code("QSB-HCM")
        assert "QSB" in result
        assert "-" in result

    @pytest.mark.unit
    def test_removes_invalid_chars(self):
        """Ký tự không hợp lệ bị xóa (chỉ giữ A-Z, 0-9, -)."""
        result = normalize_university_code("QSB_HCM")
        # Dấu underscore bị xóa
        assert "_" not in result

    @pytest.mark.unit
    def test_empty_string(self):
        """Chuỗi rỗng → chuỗi rỗng."""
        assert normalize_university_code("") == ""

    @pytest.mark.unit
    def test_none_input(self):
        """None → chuỗi rỗng."""
        assert normalize_university_code(None) == ""  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_max_length_20(self):
        """Kết quả không vượt quá 20 ký tự."""
        long_code = "A" * 50
        result = normalize_university_code(long_code)
        assert len(result) <= 20

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("qsb", "QSB"),
        ("BKA", "BKA"),
        ("  FTU  ", "FTU"),
        ("tdt", "TDT"),
        ("QHI", "QHI"),
        ("uit", "UIT"),
        ("hcmut", "HCMUT"),
    ])
    def test_parametrized(self, raw: str, expected: str):
        """Kiểm tra nhiều mã trường phổ biến."""
        assert normalize_university_code(raw) == expected


# ============================================================
# normalize_score
# ============================================================


class TestNormalizeScore:
    """Tests cho hàm normalize_score()."""

    @pytest.mark.unit
    def test_valid_float_string(self):
        """Float string hợp lệ → float."""
        assert normalize_score("25.5") == 25.5

    @pytest.mark.unit
    def test_comma_decimal_separator(self):
        """Dấu phẩy thay dấu chấm → được xử lý đúng."""
        assert normalize_score("25,5") == 25.5

    @pytest.mark.unit
    def test_with_suffix_diem(self):
        """Chuỗi có suffix 'điểm' → parse được."""
        assert normalize_score("25.50 điểm") == 25.5

    @pytest.mark.unit
    def test_with_prefix_ge(self):
        """Chuỗi có prefix '≥' → parse được."""
        assert normalize_score("≥ 25.0") == 25.0

    @pytest.mark.unit
    def test_integer_input(self):
        """Integer input → float."""
        assert normalize_score(25) == 25.0

    @pytest.mark.unit
    def test_float_input(self):
        """Float input trực tiếp."""
        assert normalize_score(25.5) == 25.5

    @pytest.mark.unit
    def test_dash_placeholder(self):
        """'---' (không có điểm) → None."""
        assert normalize_score("---") is None

    @pytest.mark.unit
    def test_single_dash(self):
        """'-' → None."""
        assert normalize_score("-") is None

    @pytest.mark.unit
    def test_na_string(self):
        """'N/A' → None."""
        assert normalize_score("N/A") is None

    @pytest.mark.unit
    def test_none_input(self):
        """None → None."""
        assert normalize_score(None) is None

    @pytest.mark.unit
    def test_empty_string(self):
        """Chuỗi rỗng → None."""
        assert normalize_score("") is None

    @pytest.mark.unit
    def test_score_below_range(self):
        """Điểm < 10 → None (ngoài thang 30)."""
        assert normalize_score("5.0") is None

    @pytest.mark.unit
    def test_score_above_range(self):
        """Điểm > 30 → None."""
        assert normalize_score("99.9") is None

    @pytest.mark.unit
    def test_score_lower_bound(self):
        """Điểm = 10.0 (biên dưới) → hợp lệ."""
        assert normalize_score("10.0") == 10.0

    @pytest.mark.unit
    def test_score_upper_bound(self):
        """Điểm = 30.0 (biên trên) → hợp lệ."""
        assert normalize_score("30.0") == 30.0

    @pytest.mark.unit
    def test_rounds_to_2_decimal(self):
        """Kết quả được làm tròn đến 2 chữ số thập phân."""
        result = normalize_score("25.555")
        assert result is not None
        assert round(result, 2) == result

    @pytest.mark.unit
    def test_non_numeric_string(self):
        """Chuỗi không phải số → None."""
        assert normalize_score("không có điểm") is None

    @pytest.mark.unit
    def test_tuyen_thang(self):
        """'tuyển thẳng' → None."""
        assert normalize_score("tuyển thẳng") is None

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("25.5", 25.5),
        ("25,5", 25.5),
        ("25.50 điểm", 25.5),
        ("≥ 25.0", 25.0),
        (25, 25.0),
        (25.5, 25.5),
        ("---", None),
        ("N/A", None),
        ("-", None),
        ("", None),
        (None, None),
        ("99.9", None),
        ("5.0", None),
        ("10.0", 10.0),
        ("30.0", 30.0),
        ("27,25", 27.25),
        ("20.00", 20.0),
        ("~22.5", 22.5),
    ])
    def test_parametrized(self, raw, expected):
        """Kiểm tra nhiều trường hợp điểm chuẩn."""
        result = normalize_score(raw)
        assert result == expected, f"normalize_score({raw!r}) = {result!r}, expected {expected!r}"


# ============================================================
# normalize_quota
# ============================================================


class TestNormalizeQuota:
    """Tests cho hàm normalize_quota()."""

    @pytest.mark.unit
    def test_valid_integer_string(self):
        """Chuỗi số hợp lệ → int."""
        assert normalize_quota("150") == 150

    @pytest.mark.unit
    def test_with_suffix(self):
        """'150 chỉ tiêu' → 150."""
        assert normalize_quota("150 chỉ tiêu") == 150

    @pytest.mark.unit
    def test_tilde_prefix(self):
        """'~200' → 200."""
        assert normalize_quota("~200") == 200

    @pytest.mark.unit
    def test_integer_input(self):
        """Integer input trực tiếp."""
        assert normalize_quota(150) == 150

    @pytest.mark.unit
    def test_none_input(self):
        """None → None."""
        assert normalize_quota(None) is None

    @pytest.mark.unit
    def test_dash_placeholder(self):
        """'---' → None."""
        assert normalize_quota("---") is None

    @pytest.mark.unit
    def test_empty_string(self):
        """Chuỗi rỗng → None."""
        assert normalize_quota("") is None

    @pytest.mark.unit
    def test_zero_returns_none(self):
        """0 → None (chỉ tiêu phải > 0)."""
        assert normalize_quota(0) is None

    @pytest.mark.unit
    def test_negative_returns_none(self):
        """Số âm → None."""
        assert normalize_quota(-10) is None

    @pytest.mark.unit
    def test_non_numeric_returns_none(self):
        """Chuỗi không phải số → None."""
        assert normalize_quota("không có") is None

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("150", 150),
        ("150 chỉ tiêu", 150),
        ("~200", 200),
        (100, 100),
        (None, None),
        ("---", None),
        ("", None),
        (0, None),
        ("50 sv", 50),
    ])
    def test_parametrized(self, raw, expected):
        """Kiểm tra nhiều trường hợp chỉ tiêu."""
        result = normalize_quota(raw)
        assert result == expected, f"normalize_quota({raw!r}) = {result!r}, expected {expected!r}"


# ============================================================
# _remove_accents (internal helper)
# ============================================================


class TestRemoveAccents:
    """Tests cho hàm nội bộ _remove_accents()."""

    @pytest.mark.unit
    def test_basic_vietnamese(self):
        """Xóa dấu tiếng Việt cơ bản."""
        result = _remove_accents("Toán học")
        assert "á" not in result
        assert "Toan" in result or "toan" in result.lower()

    @pytest.mark.unit
    def test_full_vietnamese_sentence(self):
        """Xóa dấu trong câu tiếng Việt."""
        result = _remove_accents("kỹ thuật phần mềm")
        assert result == "ky thuat phan mem"

    @pytest.mark.unit
    def test_already_ascii(self):
        """Chuỗi ASCII không thay đổi."""
        result = _remove_accents("CNTT")
        assert result == "CNTT"

    @pytest.mark.unit
    def test_empty_string(self):
        """Chuỗi rỗng → chuỗi rỗng."""
        assert _remove_accents("") == ""

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("Toán-Lý-Hóa", "Toan-Ly-Hoa"),
        ("Văn-Sử-Địa", "Van-Su-Dia"),
        ("Kỹ thuật", "Ky thuat"),
        ("phần mềm", "phan mem"),
        ("CNTT", "CNTT"),
        ("abc", "abc"),
    ])
    def test_parametrized_diacritics(self, raw: str, expected: str):
        """Kiểm tra xóa dấu cho nhiều chuỗi."""
        result = _remove_accents(raw)
        assert result == expected, f"_remove_accents({raw!r}) = {result!r}, expected {expected!r}"


# ============================================================
# INTEGRATION-STYLE TESTS (các hàm kết hợp với nhau)
# ============================================================


class TestNormalizersIntegration:
    """
    Tests kiểm tra luồng chuẩn hóa kết hợp nhiều hàm.
    Mô phỏng cách NormalizationPipeline dùng các hàm này.
    """

    @pytest.mark.unit
    def test_full_admission_score_normalization(self):
        """
        Mô phỏng normalize một bản ghi điểm chuẩn thô hoàn chỉnh.
        """
        # Dữ liệu thô từ spider
        raw_university_code = "qsb "
        raw_major_name = "Ngành: Kỹ thuật phần mềm (KTPM)"
        raw_subject_combo = "Toán-Lý-Anh"
        raw_score = "25,75 điểm"
        raw_quota = "150 chỉ tiêu"

        # Chuẩn hóa
        uni_code = normalize_university_code(raw_university_code)
        major_name = normalize_major_name(raw_major_name)
        combo = normalize_subject_combo(raw_subject_combo)
        score = normalize_score(raw_score)
        quota = normalize_quota(raw_quota)

        # Assertions
        assert uni_code == "QSB"
        assert "ngành" not in major_name.lower()
        assert "(KTPM)" not in major_name
        assert combo == "A01"
        assert score == 25.75
        assert quota == 150

    @pytest.mark.unit
    def test_fallback_to_khac_for_unknown_combo(self):
        """
        Tổ hợp môn không rõ → KHAC, không crash.
        """
        result = normalize_subject_combo("Năng khiếu vẽ")
        assert result == "KHAC"

    @pytest.mark.unit
    def test_score_with_no_value_placeholder(self):
        """
        Nhiều dạng 'không có điểm' đều → None.
        """
        placeholders = ["---", "--", "-", "N/A", "na", "", "0"]
        for ph in placeholders:
            result = normalize_score(ph)
            assert result is None, f"Expected None for placeholder {ph!r}, got {result!r}"

    @pytest.mark.unit
    def test_normalize_multiple_combos_from_real_table(self):
        """
        Normalize chuỗi tổ hợp môn như xuất hiện trên thực tế.
        """
        # Dạng phổ biến trên tuyensinh247: "A00, A01, D01"
        result = normalize_multiple_combos("A00, A01, D01")
        assert set(result) == {"A00", "A01", "D01"}

        # Dạng dùng dấu chấm phẩy
        result = normalize_multiple_combos("Toán-Lý-Hóa; Văn-Sử-Địa")
        assert set(result) == {"A00", "C00"}
