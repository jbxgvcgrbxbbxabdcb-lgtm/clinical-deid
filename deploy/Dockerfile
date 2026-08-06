# syntax=docker/dockerfile:1.7
# Backend API only. Serve the React UI with nginx (or another reverse proxy).

FROM python:3.11-slim@sha256:e031123e3d85762b141ad1cbc56452ba69c6e722ebf2f042cc0dc86c47c0d8b3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY backend ./backend

# Install torch+torchvision from the same CPU index. A follow-up force-reinstall
# keeps them matched if `pip install .` pulls an incompatible PyPI torchvision.
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        --force-reinstall --no-deps torch torchvision

EXPOSE 7870

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://127.0.0.1:7870/api/sample >/dev/null || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7870"]
