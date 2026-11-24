FROM ghcr.io/astral-sh/uv:0.9.5 AS uv
FROM python:3.12-slim AS base
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

FROM base AS worker
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN uv pip install --python /opt/venv/bin/python playwright==1.62.0 \
    && playwright install --with-deps chromium
COPY . .
CMD ["python", "-m", "app.jobs.runner"]

FROM base AS runtime
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
