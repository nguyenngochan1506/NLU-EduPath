#!/bin/bash
# ============================================================
# NLU-EduPath – Init & Crawl Script
# Tự động nạp danh mục ngành chuẩn và cào dữ liệu Tuyensinh247
# ============================================================

set -e

# 1. Đi vào thư mục craw-data
cd "$(dirname "$0")/craw-data"

# 2. Kích hoạt môi trường ảo nếu tồn tại
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 3. Nạp danh mục ngành học chuẩn (Brain of the system)
echo "🧠 [SEED] Đang nạp danh mục ngành học chuẩn..."
python scripts/seed_data.py

# 4. Chạy Spider cào dữ liệu từ Tuyensinh247
# -a source=tuyensinh247: Chỉ định nguồn cào
# -a years=2024,2025: Giới hạn năm (có thể bỏ qua để cào hết)
echo "🚀 [CRAWL] Bắt đầu cào dữ liệu từ Tuyensinh247..."
scrapy crawl admission_score -a source=tuyensinh247

echo "✅ [DONE] Quá trình hoàn tất!"
