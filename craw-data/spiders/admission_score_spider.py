# ============================================================
# spiders/admission_score_spider.py
# AdmissionScoreSpider – Thu thập hồ sơ trường & điểm chuẩn 2020-2025
# ============================================================

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterator, Optional, Union
from urllib.parse import urljoin

from items import AdmissionScoreItem, UniversityItem
from scrapy.http import Request, Response
from spiders.base_spider import BaseSpider

# ============================================================
# CONSTANTS & MAPPINGS
# ============================================================

_METHOD_KEYWORDS: list[tuple[str, str]] = [
    ("tuyen thang", "xet_tuyen_thang"),
    ("xet thang", "xet_tuyen_thang"),
    ("uu tien xet tuyen", "xet_tuyen_thang"),
    ("danh gia nang luc", "DGNL"),
    ("dgnl", "DGNL"),
    ("nang luc", "DGNL"),
    ("hoc ba", "hoc_ba"),
    ("xet hoc ba", "hoc_ba"),
    ("ielts", "SAT"),
    ("toefl", "SAT"),
    ("sat", "SAT"),
    ("thpt", "THPT"),
    ("thi thpt", "THPT"),
    ("diem thi", "THPT"),
]

_COMBO_ALIAS_MAP: dict[str, str] = {
    "toan ly hoa": "A00", "t l h": "A00", "toan-ly-hoa": "A00",
    "toan ly anh": "A01", "t l a": "A01", "toan-ly-anh": "A01",
    "toan van anh": "D01", "van su dia": "C00",
}

_VALID_COMBOS: set[str] = {
    "A00", "A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10",
    "B00", "B01", "B02", "B03", "B04", "B08",
    "C00", "C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08",
    "C10", "C14", "C15", "C16", "C17", "C19", "C20",
    "D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10",
    "D11", "D12", "D13", "D14", "D15", "D78", "D79", "D80", "D81", "X06", "KHAC"
}

class AdmissionScoreSpider(BaseSpider):
    name = "admission_score"
    requires_playwright = False
    download_delay = 2.0
    allowed_domains = ["tuyensinh.moet.gov.vn", "diemthi.tuyensinh247.com", "tuyensinh247.com"]

    def __init__(self, source: str = "moet", years: str = "", university_codes: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = source.lower().strip()
        self.years = [int(y) for y in years.split(",")] if years else list(range(2020, 2026))
        self.university_codes_filter = {c.strip().upper() for c in university_codes.split(",")} if university_codes else None
        
        if self.source == "tuyensinh247":
            self.requires_playwright = True
            self.download_delay = 3.0

    def start_requests(self) -> Iterator[Request]:
        self.logger.info("🚀 [START] Nguồn: %s | Năm: %s", self.source, self.years)
        if self.source == "moet":
            yield from self._start_moet()
        elif self.source == "tuyensinh247":
            yield from self._start_tuyensinh247()
        else:
            yield from self._start_university_sites()

    # ================================================================
    # NGUỒN 1: MOET
    # ================================================================

    def _start_moet(self) -> Iterator[Request]:
        from config.spider_config import MOET
        for year in self.years:
            url = MOET["score_search_url"].format(year=year, page=1)
            yield self._make_request(url=url, callback=self._parse_moet_page, cb_kwargs={"year": year, "page": 1})

    def _parse_moet_page(self, response: Response, year: int, page: int) -> Iterator[Any]:
        rows = response.css("table tbody tr")
        for row in rows:
            cells = row.css("td")
            if len(cells) < 5: continue
            code = self._normalize_university_code(self._cell_text(cells, 0))
            if self.university_codes_filter and code not in self.university_codes_filter: continue
            
            item = AdmissionScoreItem()
            item["university_code"] = code
            item["major_name_raw"] = self._cell_text(cells, 3)
            item["major_code"] = self._normalize_major_code(self._cell_text(cells, 2))
            item["year"] = year
            item["subject_combination"] = self._normalize_combo(self._cell_text(cells, 4))
            item["cutoff_score"] = self._parse_score(self._cell_text(cells, 5))
            item["admission_method"] = self._detect_admission_method(item["major_name_raw"])
            item["scraped_at"] = self._now_utc()
            item["source_url"] = response.url
            yield item

        # Pagination
        next_link = response.css("ul.pagination li a:contains('Tiếp'), a[rel='next']::attr(href)").get()
        if next_link and page < 50:
            yield self._make_request(url=response.urljoin(next_link), callback=self._parse_moet_page, cb_kwargs={"year": year, "page": page+1})

    # ================================================================
    # NGUỒN 2: TUYENSINH247 (Catalog -> Detail -> Profile + Scores)
    # ================================================================

    def _start_tuyensinh247(self) -> Iterator[Request]:
        """
        Khởi đầu: Vào trang điểm chuẩn tổng hợp.
        """
        url = "https://diemthi.tuyensinh247.com/diem-chuan.html"
        self.logger.info("🗺️ [MAP] Đang khởi động tại trang điểm chuẩn Tuyensinh247...")
        yield self._make_request(
            url=url,
            callback=self._parse_tuyensinh247_catalog,
        )

    def _parse_tuyensinh247_catalog(self, response: Response) -> Iterator[Request]:
        """Parse trang danh sách trường từ list-schol-box."""
        items = response.css(".list-schol-box ul li a")
        
        count = 0
        for a in items:
            href = a.attrib.get("href", "")
            text = "".join(a.css("::text").getall())
            # Format: "KHA - Đại Học Kinh Tế Quốc Dân"
            match = re.search(r"^\s*([A-Z0-9]{2,10})\s*-\s*(.+)$", text)
            
            university_code = match.group(1).strip() if match else None
            name = match.group(2).strip() if match else text
            
            if not university_code:
                # Thử lấy từ slug nếu text không khớp regex
                university_code = self._extract_code_from_slug(href)
            
            if not university_code: continue

            if self.university_codes_filter and university_code.upper() not in self.university_codes_filter:
                continue

            count += 1
            abs_url = response.urljoin(href)
            
            yield self._make_request(
                url=abs_url,
                callback=self._parse_tuyensinh247_university,
                cb_kwargs={
                    "university_code": university_code,
                    "university_name": name
                }
            )
            
        self.logger.info("📡 [READY] Đã tìm thấy %d trường từ Tuyensinh247.", count)

    def _parse_tuyensinh247_university(self, response: Response, university_code: str, university_name: str) -> Iterator[Union[UniversityItem, AdmissionScoreItem]]:
        now = self._now_utc()

        # 1. LƯU THÔNG TIN TRƯỜNG
        uni = UniversityItem()
        uni["university_code"] = university_code
        uni["name"] = university_name
        uni["short_name"] = university_code
        uni["scraped_at"] = now
        uni["source_url"] = response.url
        uni["university_type"] = "public" # Mặc định
        
        # Thử lấy thêm info nếu có
        info_text = " ".join(response.css(".box-info-school ::text, .content-school ::text").getall())
        if info_text:
            website = re.search(r"(?:Website|Web):\s*([^\s,;]+)", info_text, re.I)
            if website: uni["website"] = website.group(1).strip("/")
            
            address = re.search(r"(?:Địa chỉ|Trụ sở):\s*([^;.\n]+)", info_text, re.I)
            if address: 
                uni["address"] = address.group(1).strip()
                addr = uni["address"].lower()
                uni["region"] = "north" if any(x in addr for x in ["hà nội", "thái nguyên", "phú thọ"]) else ("central" if any(x in addr for x in ["đà nẵng", "huế"]) else "south")
                uni["province"] = uni["address"].split(",")[-1].strip()

        yield uni

        # 2. LẤY ĐIỂM CHUẨN CÁC NĂM
        # Cấu trúc mới: <div class="cutoff-table" id="diem-thi-thpt"> ... <h3> ... năm 2025 ... </h3>
        tables_containers = response.css(".cutoff-table")
        for container in tables_containers:
            title = "".join(container.css("h3 ::text").getall()).lower()
            
            # Tìm năm từ tiêu đề
            year_match = re.search(r"năm\s+(\d{4})", title)
            year = int(year_match.group(1)) if year_match else now.year
            
            if self.years and year not in self.years:
                continue

            method = self._detect_admission_method(title)
            
            rows = container.css("table tbody tr")
            for row in rows:
                cells = row.css("td")
                if len(cells) < 3: continue
                
                # Tên ngành | Tổ hợp | Điểm chuẩn | Ghi chú
                major_name = self._cell_text(cells, 0)
                combo_raw = self._cell_text(cells, 1)
                score_raw = self._cell_text(cells, 2)
                note = self._cell_text(cells, 3) if len(cells) > 3 else ""

                if not major_name or "tên ngành" in major_name.lower(): continue

                # Một dòng có thể chứa nhiều tổ hợp cách nhau bởi dấu phẩy
                combos = [c.strip() for c in combo_raw.split(",")] if combo_raw else ["KHAC"]
                
                for c in combos:
                    item = AdmissionScoreItem()
                    item["university_code"] = university_code
                    item["major_name_raw"] = major_name
                    item["year"] = year
                    item["subject_combination"] = self._normalize_combo(c)
                    item["cutoff_score"] = self._parse_score(score_raw)
                    item["admission_method"] = method
                    item["note"] = note
                    item["scraped_at"] = now
                    item["source_url"] = response.url
                    yield item

    # ================================================================
    # NGUỒN 3: UNIVERSITY SITES – Crawl trực tiếp từ web trường
    # ================================================================

    def _start_university_sites(self) -> Iterator[Request]:
        from config.spider_config import UNIVERSITY_SITES, get_university_config
        codes = self.university_codes_filter if self.university_codes_filter else set(UNIVERSITY_SITES.keys())
        for code in codes:
            config = get_university_config(code)
            url = config.get("score_url")
            if not url: continue
            self.logger.info("[uni_site] Bắt đầu trường %s | URL=%s", code, url)
            req_playwright = config.get("requires_playwright", self.requires_playwright)
            if req_playwright:
                yield self._make_playwright_request(url=url, callback=self._parse_university_site, wait_for_selector=config.get("wait_for_selector", "table"), cb_kwargs={"university_code": code, "config": config})
            else:
                yield self._make_request(url=url, callback=self._parse_university_site, cb_kwargs={"university_code": code, "config": config})

    def _parse_university_site(self, response: Response, university_code: str, config: dict) -> Iterator[AdmissionScoreItem]:
        tables = response.css(config.get("score_table_selector", "table"))
        current_year = self.years[-1] if self.years else 2024
        total = 0
        for table in tables:
            rows = table.css(config.get("score_row_selector", "tbody tr")) or table.css("tr")
            for row in rows:
                cells = row.css("td")
                if len(cells) < 2: continue
                major_name_raw = self._extract_cell_by_config(cells, config, "col_major_name")
                cutoff_raw = self._extract_cell_by_config(cells, config, "col_cutoff_score")
                if not major_name_raw or not cutoff_raw: continue
                item = AdmissionScoreItem()
                item["university_code"] = university_code
                item["major_name_raw"] = major_name_raw.strip()
                item["year"] = current_year
                item["admission_method"] = self._detect_admission_method(major_name_raw)
                item["subject_combination"] = self._normalize_combo(self._extract_cell_by_config(cells, config, "col_subject_combo"))
                item["cutoff_score"] = self._parse_score(cutoff_raw)
                item["scraped_at"] = self._now_utc()
                item["source_url"] = response.url
                total += 1
                yield item
        self.logger.info("[%s] Yield %d items từ website trường", university_code, total)

    def _extract_cell_by_config(self, cells, config, key):
        selector = config.get(key)
        if not selector: return ""
        match = re.search(r"nth-child\((\d+)\)", selector)
        if match:
            idx = int(match.group(1)) - 1
            if idx < len(cells): return self._cell_text(cells, idx)
        return ""

    def _cell_text(self, cells, index: int) -> str:
        if index < 0 or index >= len(cells): return ""
        return " ".join(cells[index].css("::text").getall()).strip()

    def _normalize_university_code(self, raw: str) -> str:
        return re.sub(r"[^\w-]", "", raw.strip().upper()) if raw else ""

    def _normalize_major_code(self, raw: str) -> Optional[str]:
        m = re.search(r"\d{7}", raw)
        return m.group(0) if m else None

    def _normalize_combo(self, raw: str) -> str:
        if not raw: return "KHAC"
        txt = _remove_accents(raw).lower()
        for k, v in _COMBO_ALIAS_MAP.items():
            if k in txt: return v
        m = re.search(r"[A-Z]\d{2}", raw.upper())
        return m.group(0) if m else "KHAC"

    def _parse_score(self, raw: str) -> Optional[float]:
        from utils.text_normalizer import normalize_score
        return normalize_score(raw)

    def _parse_quota(self, raw: str) -> Optional[int]:
        from utils.text_normalizer import normalize_quota
        return normalize_quota(raw)

    def _detect_admission_method(self, text: str) -> str:
        txt = _remove_accents(text).lower()
        for k, m in _METHOD_KEYWORDS:
            if k in txt: return m
        return "THPT"

    def _detect_table_admission_method(self, response, table, idx):
        txt = " ".join(table.xpath("preceding-sibling::h2[1]/text() | preceding-sibling::h3[1]/text()").getall()).lower()
        return self._detect_admission_method(txt) if txt else None

    def _extract_slug_from_url(self, url: str):
        m = re.search(r"/diem-chuan[/-](.+?)(?:\.html|$)", url)
        return m.group(1) if m else None

    def _extract_code_from_slug(self, slug: str):
        parts = slug.split("-")
        return parts[-1].upper() if parts else None

def _remove_accents(text: str) -> str:
    if not text: return ""
    nkfd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nkfd if not unicodedata.combining(c)).replace("đ", "d").replace("Đ", "D")
