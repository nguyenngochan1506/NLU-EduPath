# ============================================================
# db/migrations/env.py
# Alembic environment configuration
#
# Chạy migration:
#   alembic upgrade head       # Áp dụng tất cả migration mới nhất
#   alembic downgrade -1       # Rollback 1 bước
#   alembic revision --autogenerate -m "your message"  # Tạo migration mới
# ============================================================

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ============================================================
# Thêm thư mục gốc của project vào sys.path
# để import được models và config
# ============================================================
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # craw-data/
sys.path.insert(0, str(_PROJECT_ROOT))

# Alembic Config object – truy cập vào alembic.ini
config = context.config

# Cấu hình logging từ alembic.ini (nếu có section [loggers])
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================
# Import Base metadata để autogenerate biết các bảng cần migrate
# ============================================================
from models import Base  # noqa: E402 – phải import sau khi sửa sys.path

target_metadata = Base.metadata

# ============================================================
# Lấy DATABASE_URL từ biến môi trường hoặc settings
# Ưu tiên: ENV var > alembic.ini sqlalchemy.url
# ============================================================


def _get_database_url() -> str:
    """
    Lấy database URL theo thứ tự ưu tiên:
    1. Biến môi trường DATABASE_URL
    2. File .env (qua python-dotenv)
    3. config.get_main_option("sqlalchemy.url") từ alembic.ini

    Returns:
        PostgreSQL DSN string
    """
    # Thử load từ .env trước
    try:
        from dotenv import load_dotenv

        env_file = _PROJECT_ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass

    # Ưu tiên biến môi trường
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    # Fallback về settings.py
    try:
        from config.settings import DATABASE_URL

        return DATABASE_URL
    except ImportError:
        pass

    # Fallback về alembic.ini
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url

    raise RuntimeError(
        "Không tìm thấy DATABASE_URL. "
        "Hãy set biến môi trường DATABASE_URL hoặc cấu hình sqlalchemy.url trong alembic.ini."
    )


# ============================================================
# Run migrations – OFFLINE MODE
# (Tạo SQL script mà không kết nối thực sự đến DB)
# ============================================================


def run_migrations_offline() -> None:
    """
    Chạy migration ở chế độ offline – sinh ra SQL script thay vì
    thực thi trực tiếp. Hữu ích để review migration trước khi apply.

    Cách chạy:
        alembic upgrade head --sql > migration.sql
    """
    url = _get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render AS `` cho UUID type ở PostgreSQL
        render_as_batch=False,
        # Compare server default để phát hiện thay đổi default values
        compare_server_default=True,
        # Include schema (None = dùng default public schema)
        include_schemas=False,
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# Run migrations – ONLINE MODE
# (Kết nối trực tiếp đến DB và apply migration)
# ============================================================


def run_migrations_online() -> None:
    """
    Chạy migration ở chế độ online – kết nối trực tiếp đến PostgreSQL
    và apply các thay đổi.

    Sử dụng NullPool để tránh giữ connection sau khi migration xong.
    """
    url = _get_database_url()

    # Override sqlalchemy.url trong config với URL đã resolve
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Không dùng connection pool cho migration
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # So sánh kiểu dữ liệu khi autogenerate
            compare_type=True,
            # So sánh server default
            compare_server_default=True,
            # Include schema
            include_schemas=False,
            # Render batch operations (dùng cho SQLite, không cần cho PostgreSQL)
            render_as_batch=False,
            # Transaction per migration (mặc định True cho PostgreSQL)
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================
# Entry point
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
