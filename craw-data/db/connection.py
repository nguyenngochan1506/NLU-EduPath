# ============================================================
# db/connection.py – SQLAlchemy Engine & Session Factory
# ============================================================
# Quản lý kết nối PostgreSQL cho toàn bộ hệ thống crawl.
# Sử dụng SQLAlchemy 2.0 synchronous engine (phù hợp với Scrapy).
# ============================================================

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# ============================================================
# Engine singleton – khởi tạo một lần, tái sử dụng toàn app
# ============================================================
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine(database_url: str | None = None) -> Engine:
    """
    Trả về SQLAlchemy Engine (singleton).

    Nếu chưa khởi tạo, tạo mới từ database_url.
    Nếu database_url không được truyền, đọc từ settings.

    Args:
        database_url: PostgreSQL DSN, VD:
            "postgresql://crawler:pass@localhost:5432/nlu_edupath"

    Returns:
        SQLAlchemy Engine đã kết nối

    Raises:
        OperationalError: Nếu không thể kết nối đến PostgreSQL
    """
    global _engine

    if _engine is not None:
        return _engine

    if database_url is None:
        from config.settings import DATABASE_URL

        database_url = DATABASE_URL

    logger.info("Khởi tạo SQLAlchemy engine: %s", _mask_url(database_url))

    _engine = create_engine(
        database_url,
        # Pool settings
        pool_size=5,  # Số kết nối giữ trong pool
        max_overflow=10,  # Kết nối bổ sung khi pool đầy
        pool_timeout=30,  # Giây chờ lấy kết nối từ pool
        pool_recycle=1800,  # Recycle kết nối sau 30 phút (tránh stale conn)
        pool_pre_ping=True,  # Test kết nối trước khi dùng
        # Echo
        echo=False,  # True để in SQL ra console (debug)
        echo_pool=False,
    )

    # Đặt timezone mặc định cho mọi kết nối mới
    @event.listens_for(_engine, "connect")
    def set_timezone(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET TIME ZONE 'Asia/Ho_Chi_Minh'")
        cursor.close()

    logger.info("Engine khởi tạo thành công.")
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker:
    """
    Trả về sessionmaker factory (singleton).

    Dùng để tạo Session trong pipelines và repositories.
    """
    global _SessionFactory

    if _SessionFactory is not None:
        return _SessionFactory

    engine = get_engine(database_url)
    _SessionFactory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,  # Tránh lazy load sau commit
    )

    return _SessionFactory


@contextmanager
def get_session(database_url: str | None = None) -> Generator[Session, None, None]:
    """
    Context manager trả về một Session đã mở.

    Tự động commit khi thoát bình thường, rollback khi có exception.

    Cách dùng:
        with get_session() as session:
            session.add(record)
            # commit tự động khi thoát block

    Args:
        database_url: DSN PostgreSQL (optional, mặc định dùng settings)

    Yields:
        sqlalchemy.orm.Session
    """
    factory = get_session_factory(database_url)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection(database_url: str | None = None) -> bool:
    """
    Kiểm tra kết nối đến PostgreSQL.

    Returns:
        True nếu kết nối thành công, False nếu lỗi.
    """
    try:
        engine = get_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Kết nối PostgreSQL: OK")
        return True
    except OperationalError as e:
        logger.error("Kết nối PostgreSQL thất bại: %s", e)
        return False


def dispose_engine() -> None:
    """
    Đóng tất cả kết nối trong pool và giải phóng engine.
    Gọi khi ứng dụng tắt hoặc khi cần reset.
    """
    global _engine, _SessionFactory

    if _engine is not None:
        _engine.dispose()
        logger.info("Engine đã được dispose.")
        _engine = None
        _SessionFactory = None


# ============================================================
# Helpers
# ============================================================


def _mask_url(url: str) -> str:
    """
    Ẩn password trong DSN để log an toàn.

    VD: postgresql://crawler:SECRET@localhost/db
     →  postgresql://crawler:****@localhost/db
    """
    import re

    return re.sub(r"(:)([^:@/]+)(@)", r"\1****\3", url)
