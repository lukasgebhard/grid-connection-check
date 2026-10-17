FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev
COPY gridcheck ./gridcheck

FROM python:3.14-slim
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app /app
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8080
CMD ["uvicorn", "gridcheck.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
