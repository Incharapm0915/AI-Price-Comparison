# Pinned to bookworm (Debian 12) explicitly — the floating `python:3.11-slim`
# tag currently resolves to trixie (Debian 13), which `playwright install
# --with-deps` doesn't yet have a matching dependency package list for
# (it falls back to an ubuntu20.04 list referencing packages trixie's repos
# no longer carry, e.g. ttf-ubuntu-font-family/ttf-unifont, and fails).
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
