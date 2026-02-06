FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt
COPY server.py .
COPY lib/ lib/
COPY workspace/ workspace/
ENTRYPOINT ["python", "server.py"]
