FROM python:3.13-slim-bookworm

ENV PYTHONPATH=/qsmith/app \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /qsmith

# `oracledb` works in thin mode without Oracle Instant Client.
# `pymssql` uses FreeTDS for MSSQL connectivity.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  freetds-dev \
  && rm -rf /var/lib/apt/lists/*

COPY docker-requirements.txt ./requirements.txt
COPY alembic.ini ./alembic.ini

# `docker-requirements.txt` can contain Windows-only transitive deps when generated on Windows.
RUN grep -v '^pywin32==' requirements.txt > requirements.linux.txt \
  && pip install -r requirements.linux.txt \
  && rm requirements.linux.txt

COPY alembic ./alembic/

COPY app/ ./app/

ENTRYPOINT ["uvicorn", "main:app"]
CMD ["--host", "0.0.0.0", "--port", "9082"]

