FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py tables.py convert.py index.html ./

# Datasets live here (made by download.sh); mounted from the host so they survive rebuilds.
RUN mkdir -p /app/data
VOLUME /app/data

EXPOSE 8002

# --proxy-headers: runs behind nginx-proxy in production (HTTPS terminates there)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002", "--proxy-headers", "--forwarded-allow-ips", "*"]
