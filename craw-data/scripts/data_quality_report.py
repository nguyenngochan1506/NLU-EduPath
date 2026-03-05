# ============================================================
# scripts/data_quality_report.py
# Báo cáo chất lượng dữ liệu sau mỗi lần crawl
# ============================================================

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Thêm thư mục gốc vào sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

# --- ANSI Colors ---
def _bold(text: str) -> str: return f"\033[1m{text}\033[0m"
def _dim(text: str) -> str: return f"\033[2m{text}\033[0m"
def _ok(text: str) -> str: return f"\033[92m{text}\033[0m"
def _warn(text: str) -> str: return f"\033[93m{text}\033[0m"
def _err(text: str) -> str: return f"\033[91m{text}\033[0m"

def _render_bar(val: int, max_val: int, width: int = 20) -> str:
    if max_val <= 0: return " " * width
    filled = int(width * val / max_val)
    return "[" + "#" * filled + " " * (width - filled) + "]"

class DataQualityReport:
    def __init__(self, session: Any) -> None:
        self._session = session
        self._report: dict[str, Any] = {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "sections": {}
        }

    def _query(self, sql: str) -> list[dict]:
        from sqlalchemy import text
        result = self._session.execute(text(sql))
        return [dict(row._mapping) for row in result]

    def _scalar(self, sql: str) -> Any:
        from sqlalchemy import text
        return self._session.execute(text(sql)).scalar()

    def run(self) -> None:
        print(_bold("\n" + "="*60))
        print(_bold("       BÁO CÁO CHẤT LƯỢNG DỮ LIỆU NLU-EDUPATH"))
        print(_bold("="*60))

        self._section_overview()
        self._section_universities()
        self._section_majors()
        self._section_admission_scores()
        self._section_crawl_logs()

    def _section_overview(self) -> None:
        print(_bold("\n▶ 1. TỔNG QUAN"))
        tables = [
            ("universities", "Trường đại học"),
            ("majors", "Ngành học"),
            ("admission_scores", "Điểm chuẩn"),
        ]
        for table, label in tables:
            count = self._scalar(f"SELECT COUNT(*) FROM {table}") or 0
            print(f"  {label:<20}: {_bold(str(count))} bản ghi")

    def _section_universities(self) -> None:
        print(_bold("\n▶ 2. TRƯỜNG ĐẠI HỌC"))
        total = self._scalar("SELECT COUNT(*) FROM universities") or 0
        active = self._scalar("SELECT COUNT(*) FROM universities WHERE is_active = true") or 0
        print(f"  Tổng số: {total} (Active: {active})")

    def _section_majors(self) -> None:
        print(_bold("\n▶ 3. NGÀNH HỌC"))
        total = self._scalar("SELECT COUNT(*) FROM majors") or 0
        has_holland = self._scalar("SELECT COUNT(*) FROM majors WHERE jsonb_array_length(holland_types) > 0") or 0
        print(f"  Tổng số: {total}")
        pct = (has_holland / total * 100) if total > 0 else 0
        print(f"  Đã gán Holland: {has_holland} ({pct:.1f}%)")

    def _section_admission_scores(self) -> None:
        print(_bold("\n▶ 4. ĐIỂM CHUẨN"))
        total = self._scalar("SELECT COUNT(*) FROM admission_scores") or 0
        print(f"  Tổng số: {total} bản ghi")

    def _section_crawl_logs(self) -> None:
        print(_bold("\n▶ 5. LỊCH SỬ CRAWL (Gần nhất)"))
        logs = self._query("SELECT spider_name, status, started_at, records_new, records_failed FROM crawl_logs ORDER BY started_at DESC LIMIT 5")
        if not logs:
            print("  (Chưa có dữ liệu)")
            return
        for log in logs:
            status_raw = log['status']
            if status_raw == 'success': status_str = _ok("SUCCESS")
            elif status_raw in ('failed', 'partial'): status_str = _err(status_raw.upper())
            else: status_str = status_raw.upper()
            
            print(f"  {log['started_at']} | {log['spider_name']:<15} | {status_str:<10} | +{log['records_new']:>4} new | {log['records_failed']:>4} fail")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", action="store_true")
    args = parser.parse_args()

    from db.connection import get_session_factory
    factory = get_session_factory()
    with factory() as session:
        report = DataQualityReport(session)
        report.run()

if __name__ == "__main__":
    main()
