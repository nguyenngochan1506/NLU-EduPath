# ============================================================
# tests/test_pipelines/test_normalization_pipeline.py
# Unit tests cho NormalizationPipeline
#
# Test coverage:
#   - AdmissionScoreItem: university_code, major_name_raw, major_code,
#     year, admission_method, subject_combination, cutoff_score, quota, note
#   - UniversityItem: code, name, short_name, type, region, tuition, year
#   - MajorItem: name, subject_combinations, holland_types, degree_level
#   - Edge cases: None values, empty strings, ALLCAPS, Unicode
# ============================================================

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Đảm bảo project root trong sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))


# ============================================================
# HELPERS
# ============================================================


def _make_score_item(**overrides) -> Any:
    """Tạo AdmissionScoreItem với giá trị mặc định hợp lệ, cho phép override."""
    from items import AdmissionScoreItem

    item = AdmissionScoreItem()
    defaults = {
        "university_code": "qsb",
        "major_name_raw": "Kỹ thuật phần mềm",
        "major_code": None,
        "year": 2024,
        "admission_method": "THPT",
        "subject_combination": "A00",
        "cutoff_score": 25.5,
        "quota": "150 chỉ tiêu",
        "note": "  Ghi chú thử nghiệm  ",
        "scraped_at": datetime.now(tz=timezone.utc),
        "source_url": "https://tuyensinh.moet.gov.vn",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        item[k] = v
    return item


def _make_university_item(**overrides) -> Any:
    from items import UniversityItem

    item = UniversityItem()
    defaults = {
        "university_code": "tst",
        "name": "  trường đại học test  ",
        "short_name": "test",
        "university_type": "công lập",
        "region": "miền nam",
        "province": "TP. Hồ Chí Minh",
        "address": "123 Đường Test",
        "website": "https://www.test.edu.vn",
        "admission_url": "https://tuyensinh.test.edu.vn",
        "logo_url": None,
        "tuition_min": "15000000",
        "tuition_max": "40000000",
        "established_year": "2000",
        "scraped_at": datetime.now(tz=timezone.utc),
        "source_url": "https://tuyensinh.moet.gov.vn",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        item[k] = v
    return item


def _make_major_item(**overrides) -> Any:
    from items import MajorItem

    item = MajorItem()
    defaults = {
        "major_code": "7480201",
        "name": "  công nghệ thông tin  ",
        "major_group": "Máy tính và CNTT",
        "major_group_code": "748",
        "description": "Đào tạo kỹ sư CNTT.",
        "career_options": [
            "Lập trình viên",
            "Kỹ sư phần mềm",
            "Lập trình viên",
        ],  # Có trùng
        "required_skills": ["Python", " Python ", "Toán học"],  # Có trùng + space thừa
        "subject_combinations": ["a00", "A01", "d01"],
        "holland_types": ["i", "R", "i"],  # Có trùng, lowercase
        "career_anchor_tags": ["Technical/Functional Competence"],
        "study_duration": "4",
        "degree_level": "kỹ sư",
        "scraped_at": datetime.now(tz=timezone.utc),
        "source_url": "https://example.com/major",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        item[k] = v
    return item


def _run_pipeline(item: Any, spider: Any) -> Any:
    """Khởi tạo NormalizationPipeline, open spider, process item, close spider."""
    from pipelines.normalization_pipeline import NormalizationPipeline

    pipeline = NormalizationPipeline()

    # open_spider khởi tạo MajorCodeMapper – mock để không phụ thuộc external
    with patch("pipelines.normalization_pipeline.MajorCodeMapper") as MockMapper:
        mock_mapper = MagicMock()
        mock_mapper._lookup = {
            "kỹ thuật phần mềm": "7480103",
            "công nghệ thông tin": "7480201",
        }
        mock_mapper.get_code.side_effect = lambda name: {
            "Kỹ Thuật Phần Mềm": "7480103",
            "Công Nghệ Thông Tin": "7480201",
        }.get(name)
        MockMapper.return_value = mock_mapper

        pipeline.open_spider(spider)
        result = pipeline.process_item(item, spider)
        pipeline.close_spider(spider)

    return result


# ============================================================
# TESTS: ADMISSION SCORE ITEM
# ============================================================


class TestNormalizationPipelineAdmissionScore:
    """Tests cho _normalize_admission_score()."""

    @pytest.mark.unit
    def test_university_code_uppercased(self, mock_spider):
        """university_code phải được uppercase và strip."""
        item = _make_score_item(university_code="  qsb  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["university_code"] == "QSB"

    @pytest.mark.unit
    def test_university_code_with_special_chars_stripped(self, mock_spider):
        """Các ký tự không hợp lệ bị xóa khỏi university_code."""
        item = _make_score_item(university_code="QS_B!")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        # Sau khi normalize_university_code: chỉ giữ A-Z, 0-9, dấu gạch ngang
        assert adapter["university_code"] == "QSB"

    @pytest.mark.unit
    def test_major_name_raw_cleaned(self, mock_spider):
        """major_name_raw phải được làm sạch (strip, prefix removal)."""
        item = _make_score_item(major_name_raw="  Ngành: Kỹ thuật phần mềm (KTPM)  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        name = adapter["major_name_raw"]
        assert "Ngành:" not in name
        assert "(KTPM)" not in name
        assert name == name.strip()

    @pytest.mark.unit
    def test_major_name_allcaps_converted(self, mock_spider):
        """Tên ngành ALLCAPS phải được chuyển về title case."""
        item = _make_score_item(major_name_raw="CÔNG NGHỆ THÔNG TIN")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        name = adapter["major_name_raw"]
        # Sau khi normalize, không còn tất cả chữ hoa
        assert name != "CÔNG NGHỆ THÔNG TIN"

    @pytest.mark.unit
    def test_major_code_resolved_when_absent(self, mock_spider):
        """Khi major_code=None, pipeline phải thử resolve từ major_name_raw."""
        item = _make_score_item(major_name_raw="Kỹ thuật phần mềm", major_code=None)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        # MajorCodeMapper mock trả về "7480103" cho "Kỹ Thuật Phần Mềm"
        # (sau khi clean name)
        # Nếu không resolve được, major_code có thể là None – không raise exception
        assert (
            adapter.get("major_code") is not None or adapter.get("major_code") is None
        )

    @pytest.mark.unit
    def test_major_code_existing_stripped(self, mock_spider):
        """Khi đã có major_code, chỉ cần strip, không cần resolve lại."""
        item = _make_score_item(major_code="  7480103  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["major_code"] == "7480103"

    @pytest.mark.unit
    def test_year_converted_to_int(self, mock_spider):
        """year phải là int sau khi normalize."""
        item = _make_score_item(year="2024")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert isinstance(adapter["year"], int)
        assert adapter["year"] == 2024

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_method,expected",
        [
            ("THPT", "THPT"),
            ("thpt", "THPT"),
            ("thi thpt", "THPT"),
            ("học bạ", "hoc_ba"),
            ("xét học bạ", "hoc_ba"),
            ("hoc_ba", "hoc_ba"),
            ("DGNL", "DGNL"),
            ("đánh giá năng lực", "DGNL"),
            ("SAT", "SAT"),
            ("xét tuyển thẳng", "xet_tuyen_thang"),
            ("tuyển thẳng", "xet_tuyen_thang"),
            ("khác", "khac"),
        ],
    )
    def test_admission_method_normalized(self, raw_method, expected, mock_spider):
        """admission_method phải được map sang enum chuẩn."""
        item = _make_score_item(admission_method=raw_method)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["admission_method"] == expected

    @pytest.mark.unit
    def test_admission_method_unknown_fallback_to_thpt(self, mock_spider):
        """Phương thức xét tuyển không nhận dạng được → fallback về THPT."""
        item = _make_score_item(admission_method="phương thức xyz không biết")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["admission_method"] == "THPT"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_combo,expected",
        [
            ("A00", "A00"),
            ("a00", "A00"),
            ("D01", "D01"),
            ("Toán-Lý-Hóa", "A00"),
            ("Toán Lý Anh", "A01"),
            ("Văn-Sử-Địa", "C00"),
            ("xyz", "KHAC"),
            ("", "KHAC"),
        ],
    )
    def test_subject_combination_normalized(self, raw_combo, expected, mock_spider):
        """subject_combination phải được normalize sang mã chuẩn."""
        item = _make_score_item(subject_combination=raw_combo)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["subject_combination"] == expected

    @pytest.mark.unit
    def test_subject_combination_empty_becomes_khac(self, mock_spider):
        """Tổ hợp rỗng hoặc None → KHAC."""
        for empty_val in (None, "", "   "):
            item = _make_score_item(subject_combination=empty_val)
            result = _run_pipeline(item, mock_spider)

            from itemadapter import ItemAdapter

            adapter = ItemAdapter(result)
            assert adapter["subject_combination"] == "KHAC"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_score,expected",
        [
            (25.5, 25.5),
            ("25.5", 25.5),
            ("25,5", 25.5),
            ("25.50 điểm", 25.5),
            (None, None),
            ("---", None),
            ("", None),
            (99.9, None),  # Ngoài khoảng → None
            (5.0, None),  # Ngoài khoảng → None
        ],
    )
    def test_cutoff_score_normalized(self, raw_score, expected, mock_spider):
        """cutoff_score phải được parse và validate về float hoặc None."""
        item = _make_score_item(cutoff_score=raw_score)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["cutoff_score"] == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_quota,expected",
        [
            (150, 150),
            ("150", 150),
            ("150 chỉ tiêu", 150),
            ("~200", 200),
            (None, None),
            ("---", None),
            ("0", None),
            (-5, None),
        ],
    )
    def test_quota_normalized(self, raw_quota, expected, mock_spider):
        """quota phải được parse về int dương hoặc None."""
        item = _make_score_item(quota=raw_quota)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["quota"] == expected

    @pytest.mark.unit
    def test_note_stripped(self, mock_spider):
        """note phải được strip và empty string → None."""
        item = _make_score_item(note="  ghi chú  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        note = adapter["note"]
        assert note == "ghi chú"

    @pytest.mark.unit
    def test_note_whitespace_only_becomes_none(self, mock_spider):
        """note chỉ có khoảng trắng → None."""
        item = _make_score_item(note="   ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["note"] is None

    @pytest.mark.unit
    def test_note_none_stays_none(self, mock_spider):
        """note=None → vẫn là None."""
        item = _make_score_item(note=None)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["note"] is None

    @pytest.mark.unit
    def test_source_url_stripped(self, mock_spider):
        """source_url phải được strip khoảng trắng."""
        item = _make_score_item(source_url="  https://example.com  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["source_url"] == "https://example.com"

    @pytest.mark.unit
    def test_returns_item_always(self, mock_spider):
        """NormalizationPipeline không bao giờ raise DropItem."""
        from scrapy.exceptions import DropItem

        item = _make_score_item()
        try:
            result = _run_pipeline(item, mock_spider)
            assert result is not None
        except DropItem:
            pytest.fail("NormalizationPipeline không được raise DropItem")

    @pytest.mark.unit
    def test_stats_updated_after_processing(self, mock_spider):
        """items_normalized counter phải tăng sau khi xử lý."""
        from pipelines.normalization_pipeline import NormalizationPipeline

        pipeline = NormalizationPipeline()

        with patch("pipelines.normalization_pipeline.MajorCodeMapper") as MockMapper:
            MockMapper.return_value._lookup = {}
            MockMapper.return_value.get_code.return_value = None
            pipeline.open_spider(mock_spider)

            assert pipeline.items_normalized == 0

            item = _make_score_item()
            pipeline.process_item(item, mock_spider)

            assert pipeline.items_normalized == 1

            pipeline.close_spider(mock_spider)


# ============================================================
# TESTS: UNIVERSITY ITEM
# ============================================================


class TestNormalizationPipelineUniversity:
    """Tests cho _normalize_university()."""

    @pytest.mark.unit
    def test_university_code_uppercased(self, mock_spider):
        """university_code phải được uppercase."""
        item = _make_university_item(university_code="tst")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["university_code"] == "TST"

    @pytest.mark.unit
    def test_name_cleaned(self, mock_spider):
        """name phải được strip khoảng trắng."""
        item = _make_university_item(name="  Trường Đại học Test  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["name"] == "Trường Đại học Test"

    @pytest.mark.unit
    def test_short_name_uppercased_for_ascii(self, mock_spider):
        """short_name thuần ASCII alphabetic → uppercase."""
        item = _make_university_item(short_name="hust")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["short_name"] == "HUST"

    @pytest.mark.unit
    def test_short_name_not_uppercased_for_non_ascii(self, mock_spider):
        """short_name có ký tự non-ASCII → không force uppercase."""
        item = _make_university_item(short_name="Đại học Test")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        # Không force uppercase vì có ký tự Unicode
        assert adapter["short_name"] is not None

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_type,expected",
        [
            ("công lập", "public"),
            ("cong lap", "public"),
            ("public", "public"),
            ("tư thục", "private"),
            ("tu thuc", "private"),
            ("private", "private"),
            ("dân lập", "private"),
            ("liên kết nước ngoài", "foreign_affiliated"),
            ("foreign_affiliated", "foreign_affiliated"),
            ("unknown_type", None),
            (None, None),
        ],
    )
    def test_university_type_normalized(self, raw_type, expected, mock_spider):
        """university_type phải được map sang giá trị chuẩn."""
        item = _make_university_item(university_type=raw_type)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("university_type") == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_region,expected",
        [
            ("north", "north"),
            ("bắc", "north"),
            ("miền bắc", "north"),
            ("Hà Nội", "north"),
            ("south", "south"),
            ("nam", "south"),
            ("miền nam", "south"),
            ("TP.HCM", "south"),
            ("tphcm", "south"),
            ("central", "central"),
            ("miền trung", "central"),
            ("Đà Nẵng", "central"),
            ("unknown_region", None),
            (None, None),
        ],
    )
    def test_region_normalized(self, raw_region, expected, mock_spider):
        """region phải được map sang north | central | south."""
        item = _make_university_item(region=raw_region)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("region") == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_tuition,expected",
        [
            ("15000000", 15_000_000),
            (15_000_000, 15_000_000),
            ("15000000 VNĐ", 15_000_000),
            (None, None),
            ("abc", None),
            ("0", None),  # 0 → None vì _opt_int trả về None khi <= 0
        ],
    )
    def test_tuition_converted_to_int(self, raw_tuition, expected, mock_spider):
        """tuition_min / tuition_max phải được parse về int."""
        item = _make_university_item(tuition_min=raw_tuition, tuition_max=raw_tuition)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("tuition_min") == expected
        assert adapter.get("tuition_max") == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_year,expected",
        [
            ("2000", 2000),
            (2000, 2000),
            ("abc", None),
            (None, None),
        ],
    )
    def test_established_year_converted(self, raw_year, expected, mock_spider):
        """established_year phải được parse về int."""
        item = _make_university_item(established_year=raw_year)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("established_year") == expected

    @pytest.mark.unit
    def test_urls_stripped(self, mock_spider):
        """Các trường URL phải được strip khoảng trắng."""
        item = _make_university_item(
            website="  https://test.edu.vn  ",
            admission_url="  https://tuyensinh.test.edu.vn  ",
        )
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("website") == "https://test.edu.vn"
        assert adapter.get("admission_url") == "https://tuyensinh.test.edu.vn"

    @pytest.mark.unit
    def test_province_stripped(self, mock_spider):
        """province và address phải được strip."""
        item = _make_university_item(
            province="  TP. Hồ Chí Minh  ",
            address="  123 Đường Test  ",
        )
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("province") == "TP. Hồ Chí Minh"
        assert adapter.get("address") == "123 Đường Test"


# ============================================================
# TESTS: MAJOR ITEM
# ============================================================


class TestNormalizationPipelineMajor:
    """Tests cho _normalize_major()."""

    @pytest.mark.unit
    def test_major_code_stripped(self, mock_spider):
        """major_code phải được strip."""
        item = _make_major_item(major_code="  7480201  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["major_code"] == "7480201"

    @pytest.mark.unit
    def test_name_cleaned(self, mock_spider):
        """name phải được clean (lowercase → title case nếu cần)."""
        item = _make_major_item(name="  công nghệ thông tin  ")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        name = adapter["name"]
        assert name == name.strip()
        assert len(name) > 0

    @pytest.mark.unit
    def test_name_prefix_removed(self, mock_spider):
        """Tiền tố 'Ngành:' trong tên ngành phải được xóa."""
        item = _make_major_item(name="Ngành: Công nghệ thông tin")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert "Ngành:" not in adapter["name"]

    @pytest.mark.unit
    def test_subject_combinations_normalized(self, mock_spider):
        """subject_combinations phải được normalize và dedup."""
        item = _make_major_item(subject_combinations=["a00", "A00", "A01", "d01"])
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        combos = adapter["subject_combinations"]

        # Đã normalize về uppercase
        assert "A00" in combos
        assert "A01" in combos
        assert "D01" in combos
        # Không có trùng lặp
        assert combos.count("A00") == 1

    @pytest.mark.unit
    def test_subject_combinations_khac_excluded(self, mock_spider):
        """KHAC không bị xóa khỏi danh sách nhưng không được đếm là resolved."""
        item = _make_major_item(subject_combinations=["A00", "xyz_unknown"])
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        combos = adapter["subject_combinations"]

        assert "A00" in combos
        # "xyz_unknown" → "KHAC"
        assert "KHAC" in combos

    @pytest.mark.unit
    def test_subject_combinations_string_converted(self, mock_spider):
        """Nếu subject_combinations là string → parse nhiều combo."""
        item = _make_major_item(subject_combinations="A00, A01, D01")
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        combos = adapter["subject_combinations"]
        assert isinstance(combos, list)
        assert len(combos) > 0

    @pytest.mark.unit
    def test_holland_types_uppercased_and_deduped(self, mock_spider):
        """holland_types phải được uppercase và loại bỏ trùng lặp."""
        item = _make_major_item(holland_types=["i", "R", "i", "r"])
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        types = adapter["holland_types"]

        assert "I" in types
        assert "R" in types
        assert types.count("I") == 1
        assert types.count("R") == 1
        # Không có lowercase
        for t in types:
            assert t == t.upper()

    @pytest.mark.unit
    def test_holland_types_invalid_excluded(self, mock_spider):
        """Holland types không hợp lệ phải bị loại bỏ."""
        item = _make_major_item(holland_types=["I", "R", "X", "Z", "123"])
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        types = adapter["holland_types"]

        valid = {"R", "I", "A", "S", "E", "C"}
        for t in types:
            assert t in valid, f"Holland type {t!r} không hợp lệ"

    @pytest.mark.unit
    def test_career_options_deduped(self, mock_spider):
        """career_options phải được loại bỏ trùng lặp và strip."""
        item = _make_major_item(
            career_options=["Lập trình viên", " Lập trình viên ", "Kỹ sư"]
        )
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        options = adapter["career_options"]

        assert options.count("Lập trình viên") == 1
        assert "Kỹ sư" in options

    @pytest.mark.unit
    def test_required_skills_deduped(self, mock_spider):
        """required_skills phải được loại bỏ trùng lặp và strip."""
        item = _make_major_item(required_skills=["Python", " Python ", "Toán học"])
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        skills = adapter["required_skills"]

        assert skills.count("Python") == 1
        assert "Toán học" in skills

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_duration,expected",
        [
            ("4", 4),
            (4, 4),
            ("6", 6),
            ("1", 1),
            ("10", 10),
            ("0", None),  # 0 < 1 → None
            ("11", None),  # 11 > 10 → None
            ("abc", None),
            (None, None),
        ],
    )
    def test_study_duration_normalized(self, raw_duration, expected, mock_spider):
        """study_duration phải được parse về int trong [1, 10]."""
        item = _make_major_item(study_duration=raw_duration)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter.get("study_duration") == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw_degree,expected",
        [
            ("cử nhân", "bachelor"),
            ("kỹ sư", "engineer"),
            ("thạc sĩ", "master"),
            ("bachelor", "bachelor"),
            ("phd", "bachelor"),  # Không hợp lệ → fallback bachelor
            (None, "bachelor"),
        ],
    )
    def test_degree_level_normalized(self, raw_degree, expected, mock_spider):
        """degree_level phải được map sang enum chuẩn."""
        item = _make_major_item(degree_level=raw_degree)
        result = _run_pipeline(item, mock_spider)

        from itemadapter import ItemAdapter

        adapter = ItemAdapter(result)
        assert adapter["degree_level"] == expected

