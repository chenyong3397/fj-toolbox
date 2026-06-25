FROM python:3.12-slim

# 安装 opencv/onnxruntime 需要的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先安装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 清理 Python 编译缓存
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; exit 0

# CloudBase 云托管默认用 80 端口
ENV PORT=80

EXPOSE 80

# 生产模式用 gunicorn
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 --log-level info"]
