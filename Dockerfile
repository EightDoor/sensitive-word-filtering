# === Stage 1: dependencies + non-editable app install ===
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
# 构建本体需要源码；--no-editable 把应用包（含 dictionaries/ 词库）装进 venv
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# === Stage 2: runtime ===
FROM python:3.11-slim
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
# 非 root 运行
RUN groupadd --system swf && useradd --system --gid swf swf
# 仅需 venv（应用与词库已在 site-packages），不带 uv 与源码
COPY --from=builder /app/.venv /app/.venv
USER swf
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/app/.venv/bin/python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"]
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "sensitive_word_filtering.main:app", "--host", "0.0.0.0", "--port", "8000"]
