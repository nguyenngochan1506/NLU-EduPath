# ============================================================
# tests/conftest.py
# Shared pytest fixtures cho toàn bộ test suite
#
# Fixtures được định nghĩa ở đây có thể dùng trong bất kỳ
# test file nào mà không cần import thêm.
#
# Cách dùng:
#   def test_something(admission_score_item, mock_spider):
#       ...
# ============================================================

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# Thêm thư mục gốc vào sys.path
# ============================================================
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ============================================================
# FIXTURES: SPIDER
# ============================================================


@pytest.fixture
def mock_spider() -> MagicMock:
    """
    Mock Scrapy Spider để dùng trong pipeline tests.

    Trả về một MagicMock có các thuộc tính cơ bản của Spider:
        - name: "test_spider"
        - logger: MagicMock logger
    """
    spider = MagicMock()
    spider.name = "test_spider"
    spider.logger = MagicMock()
    return spider


@pytest.fixture
def admission_score_spider() -> MagicMock:
    """Mock AdmissionScoreSpider với các thuộc tính cụ thể."""
    spider = MagicMock()
    spider.name = "admission_score"
    spider.source = "moet"
    spider.years = [2023, 2024]
    spider.university_codes_filter = None
    spider.logger = MagicMock()
    return spider


# ============================================================
# FIXTURES: SCRAPY ITEMS
# ============================================================


@pytest.fixture
def now_utc() -> datetime:
    """Datetime hiện tại với timezone UTC."""
    return datetime.now(tz=timezone.utc)


@pytest.fixture
def admission_score_item(now_utc: datetime) -> Any:
    """
    AdmissionScoreItem hợp lệ dùng cho testing pipeline.

    Đây là item điển hình được tạo bởi AdmissionScoreSpider
    sau khi parse từ MOET hoặc tuyensinh247.
    """
    from items import AdmissionScoreItem

    item = AdmissionScoreItem()
    item["university_code"] = "QSB"
    item["major_name_raw"] = "Kỹ thuật phần mềm"
    item["major_code"] = "7480103"
    item["year"] = 2024
    item["admission_method"] = "THPT"
    item["subject_combination"] = "A00"
    item["cutoff_score"] = 25.5
    item["quota"] = 150
    item["note"] = None
    item["scraped_at"] = now_utc
    item["source_url"] = (
        "https://tuyensinh.moet.gov.vn/ts/DanhSachCoSoGiaoDuc/DSDiemChuan"
    )
    return item


@pytest.fixture
def admission_score_item_no_score(now_utc: datetime) -> Any:
    """AdmissionScoreItem không có điểm chuẩn (cutoff_score=None)."""
    from items import AdmissionScoreItem

    item = AdmissionScoreItem()
    item["university_code"] = "BKA"
    item["major_name_raw"] = "Công nghệ thông tin"
    item["major_code"] = "7480201"
    item["year"] = 2024
    item["admission_method"] = "hoc_ba"
    item["subject_combination"] = "D01"
    item["cutoff_score"] = None
    item["quota"] = None
    item["note"] = "Xét tuyển học bạ 5 học kỳ"
    item["scraped_at"] = now_utc
    item["source_url"] = "https://tuyensinh.moet.gov.vn"
    return item


@pytest.fixture
def admission_score_item_invalid() -> Any:
    """AdmissionScoreItem không hợp lệ – thiếu university_code."""
    from items import AdmissionScoreItem

    item = AdmissionScoreItem()
    item["university_code"] = ""  # Không hợp lệ
    item["major_name_raw"] = "Kỹ thuật phần mềm"
    item["year"] = 2024
    item["admission_method"] = "THPT"
    item["subject_combination"] = "A00"
    item["cutoff_score"] = 25.5
    item["scraped_at"] = datetime.now(tz=timezone.utc)
    item["source_url"] = "https://example.com"
    return item


@pytest.fixture
def admission_score_item_bad_score(now_utc: datetime) -> Any:
    """AdmissionScoreItem với điểm chuẩn ngoài khoảng [10, 30]."""
    from items import AdmissionScoreItem

    item = AdmissionScoreItem()
    item["university_code"] = "QSB"
    item["major_name_raw"] = "Kỹ thuật phần mềm"
    item["major_code"] = "7480103"
    item["year"] = 2024
    item["admission_method"] = "THPT"
    item["subject_combination"] = "A00"
    item["cutoff_score"] = 99.9  # Điểm không hợp lệ
    item["quota"] = 100
    item["note"] = None
    item["scraped_at"] = now_utc
    item["source_url"] = "https://tuyensinh.moet.gov.vn"
    return item


@pytest.fixture
def university_item(now_utc: datetime) -> Any:
    """UniversityItem hợp lệ dùng cho testing pipeline."""
    from items import UniversityItem

    item = UniversityItem()
    item["university_code"] = "TST"
    item["name"] = "Trường Đại học Test"
    item["short_name"] = "TEST"
    item["university_type"] = "public"
    item["region"] = "south"
    item["province"] = "TP. Hồ Chí Minh"
    item["address"] = "123 Đường Test, Quận 1, TP.HCM"
    item["website"] = "https://www.test.edu.vn"
    item["admission_url"] = "https://tuyensinh.test.edu.vn"
    item["logo_url"] = None
    item["tuition_min"] = 15_000_000
    item["tuition_max"] = 40_000_000
    item["established_year"] = 2000
    item["scraped_at"] = now_utc
    item["source_url"] = "https://tuyensinh.moet.gov.vn"
    return item


@pytest.fixture
def major_item(now_utc: datetime) -> Any:
    """MajorItem hợp lệ dùng cho testing pipeline."""
    from items import MajorItem

    item = MajorItem()
    item["major_code"] = "7480201"
    item["name"] = "Công Nghệ Thông Tin"
    item["major_group"] = "Máy tính và Công nghệ thông tin"
    item["major_group_code"] = "748"
    item["description"] = "Đào tạo kỹ sư CNTT"
    item["career_options"] = ["Lập trình viên", "Kỹ sư phần mềm"]
    item["required_skills"] = ["Python", "Toán học"]
    item["subject_combinations"] = ["A00", "A01", "D01"]
    item["holland_types"] = ["I", "R"]
    item["career_anchor_tags"] = ["Technical/Functional Competence"]
    item["study_duration"] = 4
    item["degree_level"] = "bachelor"
    item["scraped_at"] = now_utc
    item["source_url"] = "https://example.com/major/cntt"
    return item


# ============================================================
# FIXTURES: PIPELINE INSTANCES
# ============================================================


@pytest.fixture
def validation_pipeline():
    """Instance của ValidationPipeline đã được init."""
    from pipelines.validation_pipeline import ValidationPipeline

    pipeline = ValidationPipeline()
    return pipeline


@pytest.fixture
def normalization_pipeline():
    """Instance của NormalizationPipeline đã được init."""
    from pipelines.normalization_pipeline import NormalizationPipeline

    pipeline = NormalizationPipeline()
    return pipeline


@pytest.fixture
def dedup_pipeline_no_db():
    """
    Instance của DeduplicationPipeline KHÔNG kết nối DB/Redis.
    Chỉ dùng in-memory dedup để test nhanh.
    """
    from pipelines.dedup_pipeline import DeduplicationPipeline

    pipeline = DeduplicationPipeline()
    pipeline._session = None  # Tắt DB check
    pipeline._redis = None  # Tắt Redis check
    return pipeline


# ============================================================
# FIXTURES: MOCK DB
# ============================================================


@pytest.fixture
def mock_session() -> MagicMock:
    """
    Mock SQLAlchemy session để test pipeline mà không cần DB thật.

    Cấu hình:
        - scalar() trả về None mặc định (không tìm thấy bản ghi)
        - scalars() trả về MagicMock
        - execute() trả về MagicMock
        - add(), flush(), commit(), rollback(), close() đều là no-op
    """
    session = MagicMock()
    session.scalar.return_value = None
    session.get.return_value = None
    session.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    session.execute.return_value = MagicMock(
        fetchall=MagicMock(return_value=[]),
        fetchone=MagicMock(return_value=None),
        all=MagicMock(return_value=[]),
    )
    return session


@pytest.fixture
def mock_university_repo(mock_session: MagicMock) -> MagicMock:
    """
    Mock UniversityRepository với các method trả về kết quả mặc định.
    """
    from unittest.mock import MagicMock

    repo = MagicMock()
    repo.get_by_code.return_value = None
    repo.exists.return_value = False
    repo.get_all_codes.return_value = []
    return repo


@pytest.fixture
def mock_major_repo(mock_session: MagicMock) -> MagicMock:
    """
    Mock MajorRepository với các method trả về kết quả mặc định.
    """
    repo = MagicMock()
    repo.get_by_code.return_value = None
    repo.get_by_name_exact.return_value = None
    repo.exists.return_value = False
    repo.resolve_major_id.return_value = None
    repo.search_by_name.return_value = []
    return repo


@pytest.fixture
def mock_score_repo(mock_session: MagicMock) -> MagicMock:
    """
    Mock ScoreRepository với các method trả về kết quả mặc định.
    """
    repo = MagicMock()
    repo.find_by_composite_key.return_value = None
    repo.count_all.return_value = 0
    repo.count_by_year.return_value = 0
    return repo


# ============================================================
# FIXTURES: SAMPLE DATA
# ============================================================


@pytest.fixture
def sample_university_id() -> uuid.UUID:
    """UUID cố định dùng cho tests liên quan đến university."""
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_major_id() -> uuid.UUID:
    """UUID cố định dùng cho tests liên quan đến major."""
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def sample_university(sample_university_id: uuid.UUID, now_utc: datetime):
    """Mock University ORM object."""
    from unittest.mock import MagicMock

    university = MagicMock()
    university.id = sample_university_id
    university.university_code = "QSB"
    university.name = "Trường Đại học Bách Khoa - ĐHQG TP.HCM"
    university.short_name = "HCMUT"
    university.university_type = "public"
    university.region = "south"
    university.is_active = True
    university.scraped_at = now_utc
    return university


@pytest.fixture
def sample_major(sample_major_id: uuid.UUID, now_utc: datetime):
    """Mock Major ORM object."""
    from unittest.mock import MagicMock

    major = MagicMock()
    major.id = sample_major_id
    major.major_code = "7480103"
    major.name = "Kỹ Thuật Phần Mềm"
    major.major_group = "Máy tính và Công nghệ thông tin"
    major.major_group_code = "748"
    major.holland_types = ["I", "R"]
    major.is_active = True
    major.is_published = False
    major.scraped_at = now_utc
    return major


# ============================================================
# FIXTURES: TEXT NORMALIZER DATA
# ============================================================


@pytest.fixture
def subject_combo_test_cases() -> list[tuple[str, str]]:
    """
    Các test case cho normalize_subject_combo().
    Format: (input_raw, expected_output)
    """
    return [
        # Mã chuẩn đã đúng
        ("A00", "A00"),
        ("a00", "A00"),
        ("D01", "D01"),
        ("B08", "B08"),
        ("X06", "X06"),
        # Dạng tên đầy đủ
        ("Toán-Lý-Hóa", "A00"),
        ("Toán Lý Hóa", "A00"),
        ("toán-lý-hóa", "A00"),
        ("Toán-Lý-Anh", "A01"),
        ("Văn-Sử-Địa", "C00"),
        ("Toán-Văn-Anh", "D01"),
        ("Toán-Hóa-Sinh", "A08"),
        # Dạng alias
        ("toán lý anh", "A01"),
        ("t-l-h", "A00"),
        # Không match → KHAC
        ("xyz không rõ", "KHAC"),
        ("", "KHAC"),
        ("---", "KHAC"),
    ]


@pytest.fixture
def major_name_test_cases() -> list[tuple[str, str]]:
    """
    Các test case cho normalize_major_name().
    Format: (input_raw, expected_contains)
    Lưu ý: chỉ kiểm tra output có chứa keyword (không exact match)
    vì title case có thể khác nhau.
    """
    return [
        ("  Kỹ thuật phần mềm  ", "Kỹ"),
        ("Ngành: Công nghệ thông tin", "Công"),
        ("chuyên ngành Quản trị kinh doanh", "Quản"),
        ("CÔNG NGHỆ THÔNG TIN", "Công"),
        ("Kỹ thuật phần mềm (KTPM)", "Kỹ"),
        ("Quản trị kinh doanh [CLC]", "Quản"),
        ("1. Kỹ thuật cơ khí", "Kỹ"),
    ]


@pytest.fixture
def score_normalization_test_cases() -> list[tuple[Any, Any]]:
    """
    Test cases cho normalize_score().
    Format: (input_raw, expected_output)
    None = không parse được
    """
    return [
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
        ("99.9", None),  # Ngoài [10, 30]
        ("5.0", None),  # Ngoài [10, 30]
        ("10.0", 10.0),  # Biên dưới hợp lệ
        ("30.0", 30.0),  # Biên trên hợp lệ
    ]


# ============================================================
# FIXTURES: ADMISSION METHOD NORMALIZATION
# ============================================================


@pytest.fixture
def admission_method_test_cases() -> list[tuple[str, str]]:
    """
    Test cases cho _normalize_admission_method().
    Format: (input_raw, expected_output)
    """
    return [
        ("THPT", "THPT"),
        ("thpt", "THPT"),
        ("thi thpt", "THPT"),
        ("điểm thi thpt", "THPT"),
        ("hoc_ba", "hoc_ba"),
        ("học bạ", "hoc_ba"),
        ("xét học bạ", "hoc_ba"),
        ("DGNL", "DGNL"),
        ("đánh giá năng lực", "DGNL"),
        ("SAT", "SAT"),
        ("ielts", "SAT"),
        ("xét tuyển thẳng", "xet_tuyen_thang"),
        ("tuyển thẳng", "xet_tuyen_thang"),
        ("khác", "khac"),
        ("unknown method", "THPT"),  # Fallback
        ("", "THPT"),  # Fallback khi rỗng
    ]


# ============================================================
# PYTEST CONFIGURATION
# ============================================================


def pytest_configure(config: pytest.Config) -> None:
    """Cấu hình pytest: đăng ký custom markers."""
    config.addinivalue_line(
        "markers",
        "unit: Đánh dấu test là unit test (không cần DB/Redis)",
    )
    config.addinivalue_line(
        "markers",
        "integration: Đánh dấu test là integration test (cần DB)",
    )
    config.addinivalue_line(
        "markers",
        "slow: Đánh dấu test chậm (Playwright, crawl thật)",
    )
