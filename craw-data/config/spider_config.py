# ============================================================
# Spider Configuration – URL patterns & CSS/XPath selectors
# ============================================================
# Tách toàn bộ selector ra file này để dễ cập nhật khi website thay đổi
# mà không cần sửa code spider.
#
# QUAN TRỌNG: Kiểm tra lại selectors trước khi chạy (xem Phụ lục B)
# ============================================================

from dataclasses import dataclass, field
from typing import Optional

# ------------------------------------------------------------
# Năm thu thập điểm chuẩn
# ------------------------------------------------------------
SCORE_YEARS: list[int] = list(range(2020, 2026))  # 2020 → 2025


# ============================================================
# NGUỒN 1: diemthi.tuyensinh247.com  (Next.js / Playwright)
# ============================================================
TUYENSINH247 = {
    # URL danh sách điểm chuẩn (trang chính)
    "score_list_url": "https://diemthi.tuyensinh247.com/diem-chuan.html",
    # Trang điểm chuẩn theo năm cụ thể (nếu có)
    "score_year_url": "https://diemthi.tuyensinh247.com/diem-chuan-dai-hoc-{year}.html",
    # --- Selectors trang danh sách ---
    # Link đến từng trường ĐH
    "university_link_selector": "ul.school-list a, a[href*='/diem-chuan/']",
    # --- Selectors trang điểm chuẩn từng trường ---
    # Bảng điểm chuẩn chính
    "score_table_selector": "table",
    # Hàng dữ liệu trong bảng (bỏ qua header)
    "score_row_selector": "tbody tr",
    # Cells trong mỗi hàng
    "col_major_name": "td:nth-child(1)",
    "col_subject_combo": "td:nth-child(2)",
    "col_cutoff_score": "td:nth-child(3)",
    "col_quota": "td:nth-child(4)",
    "col_note": "td:nth-child(5)",
    # Element cần chờ trước khi extract (Playwright waitForSelector)
    "wait_for_selector": "table",
    "wait_timeout_ms": 15000,
    # Tên trường: thường nằm trong <h1> hoặc tiêu đề trang
    "university_name_selector": "h1",
    # Rate limiting
    "download_delay": 2.0,
}


# ============================================================
# NGUỒN 2: tuyensinh.moet.gov.vn  (Bộ GD&ĐT – static/ASP.NET)
# ============================================================
MOET = {
    "base_url": "https://tuyensinh.moet.gov.vn",
    "score_search_url": (
        "https://tuyensinh.moet.gov.vn/ts/DanhSachCoSoGiaoDuc/DSDiemChuan"
        "?MaTruong=&NamTuyenSinh={year}&TenTruong=&Page={page}"
    ),
    "score_row_selector": "table tbody tr",
    "col_university_code": "td:nth-child(1)",
    "col_university_name": "td:nth-child(2)",
    "col_major_code": "td:nth-child(3)",
    "col_major_name": "td:nth-child(4)",
    "col_subject_combo": "td:nth-child(5)",
    "col_cutoff_score": "td:nth-child(6)",
    "pagination_selector": "ul.pagination li a",
    "download_delay": 2.0,
    "requires_playwright": False,
}


# ============================================================
# NGUỒN 3: Website từng trường (danh sách seed)
# ============================================================
# Mỗi entry có thể override selector mặc định
UNIVERSITY_SITES: dict[str, dict] = {
    # --- TP.HCM ---
    "QSB": {
        "name": "ĐH Bách khoa TP.HCM",
        "score_url": "https://tuyensinh.hcmut.edu.vn/diem-trung-tuyen",
        "score_table_selector": "table.table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "col_quota": "td:nth-child(4)",
        "requires_playwright": True,
    },
    "QSE": {
        "name": "ĐH Kinh tế TP.HCM",
        "score_url": "https://tuyensinh.ueh.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    "QSF": {
        "name": "ĐH Nông Lâm TP.HCM",
        "score_url": "https://tuyensinh.hcmuaf.edu.vn/diem-chuan.html",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": False,
    },
    "QST": {
        "name": "ĐH Sư phạm Kỹ thuật TP.HCM",
        "score_url": "https://tuyensinh.hcmute.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    "QSI": {
        "name": "ĐH Công nghệ Thông tin (UIT)",
        "score_url": "https://tuyensinh.uit.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    "TDT": {
        "name": "ĐH Tôn Đức Thắng",
        "score_url": "https://tuyensinh.tdtu.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    # --- Hà Nội ---
    "BKA": {
        "name": "ĐH Bách khoa Hà Nội",
        "score_url": "https://ts.hust.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    "KQD": {
        "name": "ĐH Kinh tế Quốc dân",
        "score_url": "https://tuyensinh.neu.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    "FTU": {
        "name": "ĐH Ngoại thương",
        "score_url": "https://tuyensinh.ftu.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
    "QHI": {
        "name": "ĐH Công nghệ – ĐHQGHN",
        "score_url": "https://tuyensinh.uet.vnu.edu.vn/diem-chuan",
        "score_table_selector": "table",
        "score_row_selector": "tbody tr",
        "col_major_name": "td:nth-child(1)",
        "col_subject_combo": "td:nth-child(2)",
        "col_cutoff_score": "td:nth-child(3)",
        "requires_playwright": True,
    },
}

# Default fallback selectors khi university site không override
DEFAULT_UNIVERSITY_SELECTORS: dict = {
    "score_table_selector": "table",
    "score_row_selector": "tbody tr",
    "col_major_name": "td:nth-child(1)",
    "col_subject_combo": "td:nth-child(2)",
    "col_cutoff_score": "td:nth-child(3)",
    "col_quota": "td:nth-child(4)",
    "col_note": "td:nth-child(5)",
    "wait_for_selector": "table",
    "wait_timeout_ms": 15000,
    "requires_playwright": True,
    "download_delay": 2.0,
}


def get_university_config(university_code: str) -> dict:
    """
    Lấy cấu hình spider cho một trường cụ thể.
    Merge DEFAULT_UNIVERSITY_SELECTORS với override của trường đó (nếu có).
    """
    base = DEFAULT_UNIVERSITY_SELECTORS.copy()
    override = UNIVERSITY_SITES.get(university_code, {})
    base.update(override)
    return base


# ============================================================
# NGUỒN 4: TopCV (Playwright – thị trường lao động)
# Dùng cho Sprint 4
# ============================================================
TOPCV = {
    "salary_report_url": "https://topcv.vn/tra-cuu-luong",
    "job_list_url": "https://www.topcv.vn/viec-lam?page={page}",
    "wait_for_selector": "[data-testid='salary-section']",
    "wait_timeout_ms": 20000,
    "download_delay": 3.0,
    "requires_playwright": True,
}


# ============================================================
# USER-AGENT Pool  (rotate để tránh bị block)
# ============================================================
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
]
