FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY watcher ./watcher
RUN pip install --no-cache-dir .

ENV DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME /data
CMD ["tg-watcher"]
