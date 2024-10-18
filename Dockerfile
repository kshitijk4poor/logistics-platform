FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
COPY pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]