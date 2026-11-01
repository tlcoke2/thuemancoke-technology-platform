FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home gateway
COPY app.py init_db.py ./
USER gateway
CMD ["sh", "-c", "uvicorn app:from_environment --factory --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
