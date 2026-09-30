FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/schedule.db

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && useradd --uid 1000 --create-home app \
    && mkdir /data && chown app:app /data

USER app
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=1m --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "dhbw_ics.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
