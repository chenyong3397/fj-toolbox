FROM python:3.12-slim

# 安装 ddddocr / onnxruntime / opencv 需要的系统库
# Debian Trixie 中 libgl1-mesa-glx 已更名为 libgl1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先安装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple

# 复制应用代码
COPY . .

# 清理 Python 编译缓存
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; exit 0

# CloudBase 云托管默认用 80 端口
ENV PORT=80

EXPOSE 80

# 生产模式用 gunicorn
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 --log-level info"]
