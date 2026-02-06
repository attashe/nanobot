FROM python:3.12-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim-bookworm
WORKDIR /app

# Copy only installed packages from builder (no pip/setuptools bloat)
COPY --from=builder /install /usr/local

# Copy application code
COPY server.py .
COPY lib/ lib/
COPY workspace/ workspace/

# Default config/workspace lives at /root/.nanobot (mount with -v)
RUN mkdir -p /root/.nanobot

ENTRYPOINT ["python", "server.py"]
