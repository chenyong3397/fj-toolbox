FROM python:3.11-slim

WORKDIR /app

# 安装最小化依赖
COPY requirements_minimal.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制最小化应用
COPY app_minimal.py app.py

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]
