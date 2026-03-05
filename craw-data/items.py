# ============================================================
# NLU-EduPath – Scrapy Items
# Định nghĩa cấu trúc dữ liệu thô được spider sinh ra.
# Sau khi qua pipeline, dữ liệu sẽ được validate bởi Pydantic
# và lưu vào PostgreSQL qua SQLAlchemy.
# ============================================================

import scrapy


class UniversityItem(scrapy.Item):
    """
    Thông tin cơ bản của một trường đại học.
    Spider: UniversitySpider
    """

    # --- Định danh ---
    university_code = scrapy.Field()  # Mã Bộ GD&ĐT, VD: "QSB", "BKA"
    name = scrapy.Field()  # Tên đầy đủ
    short_name = scrapy.Field()  # Tên viết tắt, VD: "HCMUT", "UEH"

    # --- Phân loại ---
    university_type = scrapy.Field()  # "public" | "private" | "foreign_affiliated"
    region = scrapy.Field()  # "north" | "central" | "south"
    province = scrapy.Field()  # Tỉnh / Thành phố

    # --- Liên hệ & Web ---
    address = scrapy.Field()
    website = scrapy.Field()
    admission_url = scrapy.Field()
    logo_url = scrapy.Field()

    # --- Tuyển sinh ---
    tuition_min = scrapy.Field()  # VNĐ / năm
    tuition_max = scrapy.Field()
    established_year = scrapy.Field()

    # --- Metadata ---
    scraped_at = scrapy.Field()  # datetime ISO string
    source_url = scrapy.Field()  # URL trang đã crawl


class MajorItem(scrapy.Item):
    """
    Thông tin ngành học.
    Spider: MajorInfoSpider
    """

    # --- Định danh ---
    major_code = scrapy.Field()  # Mã ngành 7 chữ số, VD: "7480201"
    name = scrapy.Field()  # Tên ngành
    major_group = scrapy.Field()  # Tên khối ngành
    major_group_code = scrapy.Field()  # Mã khối ngành, VD: "7480"

    # --- Mô tả ---
    description = scrapy.Field()
    career_options = scrapy.Field()  # list[str]
    required_skills = scrapy.Field()  # list[str]
    subject_combinations = scrapy.Field()  # list[str], VD: ["A00", "A01"]

    # --- AI Mapping (do EnrichmentPipeline tự động điền) ---
    holland_types = scrapy.Field()  # list[str], VD: ["I", "R"]
    career_anchor_tags = scrapy.Field()  # list[str]

    # --- Đào tạo ---
    study_duration = scrapy.Field()  # Năm (int)
    degree_level = scrapy.Field()  # "bachelor" | "engineer" | "master"

    # --- Metadata ---
    scraped_at = scrapy.Field()
    source_url = scrapy.Field()


class AdmissionScoreItem(scrapy.Item):
    """
    Điểm chuẩn của một ngành tại một trường trong một năm cụ thể.
    Spider: AdmissionScoreSpider  ← Sprint 1
    """

    # --- Liên kết ---
    university_code = scrapy.Field()  # Dùng để resolve → university_id (UUID)
    major_name_raw = scrapy.Field()  # Tên ngành thô từ web (chưa chuẩn hóa)
    major_code = scrapy.Field()  # Sau khi NormalizationPipeline tra cứu

    # --- Dữ liệu điểm chuẩn ---
    year = scrapy.Field()  # int, VD: 2024
    admission_method = scrapy.Field()  # "THPT" | "hoc_ba" | "DGNL" | "SAT"
    subject_combination = scrapy.Field()  # Mã chuẩn, VD: "A00"
    cutoff_score = scrapy.Field()  # float, thang 30
    quota = scrapy.Field()  # int | None
    note = scrapy.Field()  # str | None

    # --- Metadata ---
    scraped_at = scrapy.Field()
    source_url = scrapy.Field()

    # --- Internal fields (Dùng cho Pipeline) ---
    _university_id = scrapy.Field()
    _major_id = scrapy.Field()


class JobCategoryItem(scrapy.Item):
    """
    Dữ liệu thị trường lao động theo nhóm nghề.
    Spider: JobMarketSpider  ← Sprint 4
    """

    # --- Định danh ---
    name = scrapy.Field()  # Tên nhóm nghề

    # --- Lương ---
    avg_salary_min = scrapy.Field()  # VNĐ / tháng
    avg_salary_max = scrapy.Field()
    median_salary = scrapy.Field()

    # --- Thị trường ---
    demand_level = scrapy.Field()  # "low"|"medium"|"high"|"very_high"
    growth_trend = scrapy.Field()  # "declining"|"stable"|"growing"|"booming"
    top_skills = scrapy.Field()  # list[str]
    job_count_sample = scrapy.Field()  # int | None
    related_majors = scrapy.Field()  # list[str] – major_codes

    # --- Metadata ---
    source = scrapy.Field()  # "topcv" | "vietnamworks"
    scraped_at = scrapy.Field()
    source_url = scrapy.Field()
