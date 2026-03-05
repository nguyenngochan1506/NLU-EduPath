# ============================================================
# tests/test_pipelines/test_validation_pipeline.py
# Unit tests cho ValidationPipeline (priority=100)
#
# Chạy:
#   pytest tests/test_pipelines/test_validation_pipeline.py -v
#   pytest tests/test_pipelines/test_validation_pipeline.py -v -m unit
# ============================================================

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Thêm thư mục gốc vào sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))


# ============================================================
# HELPERS
# ============================================================


def _make_item(item_class, **kwargs):
    """Tạo item với các field được truyền vào."""
    item = item_class()
    for key, value in kwargs.items():
        item[key] = value
    return item


def _now():
    return datetime.now(tz=timezone.utc)


# ============================================================
# TESTS: PIPELINE LIFECYCLE
# ============================================================


@pytest.mark.unit
class TestValidationPipelineLifecycle:
    """Kiểm tra vòng đời pipeline (open_spider, close_spider)."""

    def test_open_spider_resets_counters(self, validation_pipeline, mock_spider):
        """open_spider phải reset toàn bộ counter về 0."""
        # Arrange: giả lập đã chạy trước đó
        validation_pipeline.items_validated = 99
        validation_pipeline.items_dropped = 10
        validation_pipeline.drop_reasons = {"some reason": 5}

        # Act
        validation_pipeline.open_spider(mock_spider)

        # Assert
        assert validation_pipeline.items_validated == 0
        assert validation_pipeline.items_dropped == 0
        assert validation_pipeline.drop_reasons == {}

    def test_close_spider_does_not_raise(self, validation_pipeline, mock_spider):
        """close_spider không được raise exception."""
        validation_pipeline.open_spider(mock_spider)
        validation_pipeline.close_spider(mock_spider)  # Không raise

    def test_initial_state(self, validation_pipeline):
        """Pipeline mới khởi tạo phải có counter = 0."""
        assert validation_pipeline.items_validated == 0
        assert validation_pipeline.items_dropped == 0
        assert validation_pipeline.drop_reasons == {}


# ============================================================
# TESTS: ADMISSION SCORE ITEM – VALID CASES
# ============================================================


@pytest.mark.unit
class TestValidationPipelineAdmissionScoreValid:
    """Test ValidationPipeline với AdmissionScoreItem hợp lệ."""

    def test_valid_item_passes_through(
        self, validation_pipeline, mock_spider, admission_score_item
    ):
        """Item hợp lệ phải được trả về không bị thay đổi logic."""
        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(admission_score_item, mock_spider)

        assert result is admission_score_item
        assert validation_pipeline.items_validated == 1
        assert validation_pipeline.items_dropped == 0

    def test_valid_item_without_score_passes(
        self, validation_pipeline, mock_spider, admission_score_item_no_score
    ):
        """Item không có cutoff_score vẫn hợp lệ (score có thể None)."""
        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(
            admission_score_item_no_score, mock_spider
        )

        assert result is admission_score_item_no_score
        assert validation_pipeline.items_validated == 1

    def test_auto_fill_scraped_at_when_missing(
        self, validation_pipeline, mock_spider
    ):
        """Nếu scraped_at bị thiếu, pipeline tự điền datetime hiện tại."""
        from items import AdmissionScoreItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            scraped_at=None,  # Thiếu
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["scraped_at"] is not None
        assert isinstance(adapter["scraped_at"], datetime)

    def test_cutoff_score_rounded_to_2_decimal(
        self, validation_pipeline, mock_spider
    ):
        """cutoff_score phải được round về 2 chữ số thập phân."""
        from items import AdmissionScoreItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.567,  # Nhiều hơn 2 chữ số thập phân
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["cutoff_score"] == 25.57

    def test_quota_string_converted_to_int(
        self, validation_pipeline, mock_spider
    ):
        """quota dạng string '150' phải được chuyển thành int 150."""
        from items import AdmissionScoreItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            quota="150",  # String
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["quota"] == 150
        assert isinstance(adapter["quota"], int)

    def test_quota_zero_becomes_none(self, validation_pipeline, mock_spider):
        """quota = 0 không có nghĩa → set None."""
        from items import AdmissionScoreItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            quota=0,
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["quota"] is None

    def test_invalid_url_set_to_none(self, validation_pipeline, mock_spider):
        """source_url không hợp lệ phải được set thành None (không drop item)."""
        from items import AdmissionScoreItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            scraped_at=_now(),
            source_url="not-a-valid-url",  # Không hợp lệ
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["source_url"] is None
        assert validation_pipeline.items_validated == 1  # Không drop

    def test_invalid_cutoff_score_set_to_none(
        self, validation_pipeline, mock_spider, admission_score_item_bad_score
    ):
        """cutoff_score ngoài [10, 30] phải được set None, không drop item."""
        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(
            admission_score_item_bad_score, mock_spider
        )

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["cutoff_score"] is None
        assert validation_pipeline.items_validated == 1  # Không drop

    def test_multiple_valid_items_increment_counter(
        self, validation_pipeline, mock_spider, admission_score_item
    ):
        """Nhiều item hợp lệ phải được đếm đúng."""
        from items import AdmissionScoreItem

        item2 = _make_item(
            AdmissionScoreItem,
            university_code="BKA",
            major_name_raw="Công nghệ thông tin",
            major_code="7480201",
            year=2023,
            admission_method="THPT",
            subject_combination="A01",
            cutoff_score=22.0,
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        validation_pipeline.process_item(admission_score_item, mock_spider)
        validation_pipeline.process_item(item2, mock_spider)

        assert validation_pipeline.items_validated == 2
        assert validation_pipeline.items_dropped == 0


# ============================================================
# TESTS: ADMISSION SCORE ITEM – INVALID CASES (DROP)
# ============================================================


@pytest.mark.unit
class TestValidationPipelineAdmissionScoreInvalid:
    """Test ValidationPipeline với AdmissionScoreItem không hợp lệ."""

    def test_empty_university_code_drops_item(
        self,
        validation_pipeline,
        mock_spider,
        admission_score_item_invalid,
    ):
        """university_code rỗng phải drop item."""
        from scrapy.exceptions import DropItem

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(
                admission_score_item_invalid, mock_spider
            )

        assert validation_pipeline.items_dropped == 1

    def test_missing_university_code_drops_item(
        self, validation_pipeline, mock_spider
    ):
        """Thiếu university_code phải drop item."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            # university_code KHÔNG có
            major_name_raw="Kỹ thuật phần mềm",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

        assert validation_pipeline.items_dropped == 1

    def test_empty_major_name_raw_drops_item(
        self, validation_pipeline, mock_spider
    ):
        """major_name_raw rỗng phải drop item."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="",  # Rỗng
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_missing_year_drops_item(self, validation_pipeline, mock_spider):
        """Thiếu year phải drop item."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            # year KHÔNG có
            admission_method="THPT",
            subject_combination="A00",
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_year_below_range_drops_item(self, validation_pipeline, mock_spider):
        """year < 2018 phải drop item."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2010,  # Ngoài khoảng [2018, 2030]
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_year_above_range_drops_item(self, validation_pipeline, mock_spider):
        """year > 2030 phải drop item."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year=2099,  # Ngoài khoảng [2018, 2030]
            admission_method="THPT",
            subject_combination="A00",
            cutoff_score=25.5,
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_invalid_year_string_drops_item(
        self, validation_pipeline, mock_spider
    ):
        """year không parse được thành int phải drop item."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="QSB",
            major_name_raw="Kỹ thuật phần mềm",
            major_code="7480103",
            year="hai nghìn hai mươi bốn",  # Không parse được
            admission_method="THPT",
            subject_combination="A00",
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_drop_reason_recorded(self, validation_pipeline, mock_spider):
        """Lý do drop phải được ghi vào drop_reasons dict."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            AdmissionScoreItem,
            university_code="",  # Không hợp lệ
            major_name_raw="Kỹ thuật phần mềm",
            year=2024,
            admission_method="THPT",
            subject_combination="A00",
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

        assert len(validation_pipeline.drop_reasons) > 0

    def test_drop_counter_accumulates(self, validation_pipeline, mock_spider):
        """Nhiều item bị drop → items_dropped tăng tương ứng."""
        from items import AdmissionScoreItem
        from scrapy.exceptions import DropItem

        def make_invalid():
            return _make_item(
                AdmissionScoreItem,
                university_code="",  # Không hợp lệ
                major_name_raw="Ngành test",
                year=2024,
                scraped_at=_now(),
            )

        validation_pipeline.open_spider(mock_spider)

        for _ in range(3):
            with pytest.raises(DropItem):
                validation_pipeline.process_item(make_invalid(), mock_spider)

        assert validation_pipeline.items_dropped == 3
        assert validation_pipeline.items_validated == 0


# ============================================================
# TESTS: UNIVERSITY ITEM – VALID CASES
# ============================================================


@pytest.mark.unit
class TestValidationPipelineUniversityValid:
    """Test ValidationPipeline với UniversityItem hợp lệ."""

    def test_valid_university_item_passes(
        self, validation_pipeline, mock_spider, university_item
    ):
        """UniversityItem hợp lệ phải được pass qua."""
        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(university_item, mock_spider)

        assert result is university_item
        assert validation_pipeline.items_validated == 1

    def test_auto_fill_scraped_at_for_university(
        self, validation_pipeline, mock_spider
    ):
        """Nếu scraped_at thiếu, phải tự điền."""
        from items import UniversityItem

        item = _make_item(
            UniversityItem,
            university_code="TST",
            name="Trường Test",
            university_type="public",
            region="south",
            scraped_at=None,
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["scraped_at"] is not None

    def test_invalid_university_type_set_to_none(
        self, validation_pipeline, mock_spider
    ):
        """university_type không hợp lệ phải set None, không drop."""
        from items import UniversityItem

        item = _make_item(
            UniversityItem,
            university_code="TST",
            name="Trường Test",
            university_type="unknown_type",  # Không hợp lệ
            region="south",
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["university_type"] is None
        assert validation_pipeline.items_validated == 1

    def test_invalid_region_set_to_none(self, validation_pipeline, mock_spider):
        """region không hợp lệ phải set None, không drop."""
        from items import UniversityItem

        item = _make_item(
            UniversityItem,
            university_code="TST",
            name="Trường Test",
            university_type="public",
            region="east",  # Không hợp lệ (phải là north/central/south)
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["region"] is None
        assert validation_pipeline.items_validated == 1

    def test_invalid_url_fields_set_to_none(
        self, validation_pipeline, mock_spider
    ):
        """Các trường URL không hợp lệ phải set None."""
        from items import UniversityItem

        item = _make_item(
            UniversityItem,
            university_code="TST",
            name="Trường Test",
            university_type="public",
            region="south",
            website="not-a-url",  # Không hợp lệ
            admission_url="ftp://wrong-scheme.com",  # Không hợp lệ
            logo_url="https://valid-url.com/logo.png",  # Hợp lệ
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["website"] is None
        assert adapter["admission_url"] is None
        assert adapter["logo_url"] == "https://valid-url.com/logo.png"

    def test_established_year_out_of_range_set_to_none(
        self, validation_pipeline, mock_spider
    ):
        """established_year ngoài [1800, 2100] phải set None."""
        from items import UniversityItem

        item = _make_item(
            UniversityItem,
            university_code="TST",
            name="Trường Test",
            university_type="public",
            region="south",
            established_year=1500,  # Quá cũ
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["established_year"] is None


# ============================================================
# TESTS: UNIVERSITY ITEM – INVALID CASES (DROP)
# ============================================================


@pytest.mark.unit
class TestValidationPipelineUniversityInvalid:
    """Test ValidationPipeline với UniversityItem không hợp lệ."""

    def test_empty_university_code_drops_item(
        self, validation_pipeline, mock_spider
    ):
        """university_code rỗng phải drop item."""
        from items import UniversityItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            UniversityItem,
            university_code="",
            name="Trường Test",
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_empty_name_drops_item(self, validation_pipeline, mock_spider):
        """name rỗng phải drop item."""
        from items import UniversityItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            UniversityItem,
            university_code="TST",
            name="",  # Rỗng
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)


# ============================================================
# TESTS: MAJOR ITEM – VALID CASES
# ============================================================


@pytest.mark.unit
class TestValidationPipelineMajorValid:
    """Test ValidationPipeline với MajorItem hợp lệ."""

    def test_valid_major_item_passes(
        self, validation_pipeline, mock_spider, major_item
    ):
        """MajorItem hợp lệ phải pass qua."""
        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(major_item, mock_spider)

        assert result is major_item
        assert validation_pipeline.items_validated == 1

    def test_none_list_fields_become_empty_list(
        self, validation_pipeline, mock_spider
    ):
        """Các list fields là None phải được chuyển thành []."""
        from items import MajorItem

        item = _make_item(
            MajorItem,
            major_code="7480201",
            name="Công nghệ thông tin",
            major_group="Máy tính",
            career_options=None,       # None → []
            required_skills=None,      # None → []
            subject_combinations=None, # None → []
            holland_types=None,        # None → []
            career_anchor_tags=None,   # None → []
            study_duration=4,
            degree_level="bachelor",
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["career_options"] == []
        assert adapter["required_skills"] == []
        assert adapter["subject_combinations"] == []
        assert adapter["holland_types"] == []
        assert adapter["career_anchor_tags"] == []

    def test_invalid_degree_level_defaults_to_bachelor(
        self, validation_pipeline, mock_spider
    ):
        """degree_level không hợp lệ phải được set thành 'bachelor'."""
        from items import MajorItem

        item = _make_item(
            MajorItem,
            major_code="7480201",
            name="Công nghệ thông tin",
            career_options=[],
            required_skills=[],
            subject_combinations=[],
            holland_types=[],
            career_anchor_tags=[],
            degree_level="phd",  # Không hợp lệ
            scraped_at=_now(),
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["degree_level"] == "bachelor"
        assert validation_pipeline.items_validated == 1

    def test_auto_fill_scraped_at_for_major(
        self, validation_pipeline, mock_spider
    ):
        """scraped_at thiếu phải được tự điền."""
        from items import MajorItem

        item = _make_item(
            MajorItem,
            major_code="7480201",
            name="Công nghệ thông tin",
            career_options=[],
            required_skills=[],
            subject_combinations=[],
            holland_types=[],
            career_anchor_tags=[],
            scraped_at=None,
            source_url="https://example.com",
        )

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        from itemadapter import ItemAdapter
        adapter = ItemAdapter(result)
        assert adapter["scraped_at"] is not None


# ============================================================
# TESTS: MAJOR ITEM – INVALID CASES (DROP)
# ============================================================


@pytest.mark.unit
class TestValidationPipelineMajorInvalid:
    """Test ValidationPipeline với MajorItem không hợp lệ."""

    def test_empty_major_code_drops_item(self, validation_pipeline, mock_spider):
        """major_code rỗng phải drop item."""
        from items import MajorItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            MajorItem,
            major_code="",  # Rỗng
            name="Công nghệ thông tin",
            career_options=[],
            required_skills=[],
            subject_combinations=[],
            holland_types=[],
            career_anchor_tags=[],
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_invalid_major_code_format_drops_item(
        self, validation_pipeline, mock_spider
    ):
        """major_code không đúng định dạng 7 chữ số phải drop item."""
        from items import MajorItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            MajorItem,
            major_code="748020",   # Chỉ có 6 chữ số (thiếu 1)
            name="Công nghệ thông tin",
            career_options=[],
            required_skills=[],
            subject_combinations=[],
            holland_types=[],
            career_anchor_tags=[],
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_major_code_with_letters_drops_item(
        self, validation_pipeline, mock_spider
    ):
        """major_code chứa ký tự chữ phải drop item."""
        from items import MajorItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            MajorItem,
            major_code="748ABCD",  # Chứa chữ
            name="Công nghệ thông tin",
            career_options=[],
            required_skills=[],
            subject_combinations=[],
            holland_types=[],
            career_anchor_tags=[],
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_invalid_holland_type_drops_item(self, validation_pipeline, mock_spider):
        """Holland type không hợp lệ (không thuộc R,I,A,S,E,C) phải drop item."""
        from items import MajorItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            MajorItem,
            major_code="7480201",
            name="Công nghệ thông tin",
            holland_types=["X", "R"],  # X không hợp lệ
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)

    def test_invalid_study_duration_drops_item(self, validation_pipeline, mock_spider):
        """study_duration ngoài khoảng [1, 10] phải drop item."""
        from items import MajorItem
        from scrapy.exceptions import DropItem

        item = _make_item(
            MajorItem,
            major_code="7480201",
            name="Công nghệ thông tin",
            study_duration=15,  # Quá dài
            scraped_at=_now(),
        )

        validation_pipeline.open_spider(mock_spider)

        with pytest.raises(DropItem):
            validation_pipeline.process_item(item, mock_spider)


# ============================================================
# TESTS: UNKNOWN ITEM TYPE
# ============================================================


@pytest.mark.unit
class TestValidationPipelineUnknownItem:
    """Test ValidationPipeline với loại item không xác định."""

    def test_unknown_item_type_passes_through(self, validation_pipeline, mock_spider):
        """Loại item không biết phải được trả về nguyên vẹn."""
        import scrapy

        class UnknownItem(scrapy.Item):
            data = scrapy.Field()

        item = UnknownItem(data="test")

        validation_pipeline.open_spider(mock_spider)
        result = validation_pipeline.process_item(item, mock_spider)

        assert result is item
        assert validation_pipeline.items_validated == 0  # Không đếm là validated

