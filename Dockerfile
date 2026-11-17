FROM ghcr.io/astral-sh/uv:0.13.6 AS uv
FROM python:3.11-slim

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --python /usr/local/bin/python
COPY src ./src
COPY data/enterprise_ops.db ./data/enterprise_ops.db
USER 10001:10001
EXPOSE 8501
CMD ["/app/.venv/bin/python", "-m", "streamlit", "run", "src/app.py", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
