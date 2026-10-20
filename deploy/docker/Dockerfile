FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache

RUN apt-get update && \
    apt-get install -y --no-install-recommends libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir '.[sherpa]'
COPY configs ./configs

RUN groupadd -r -g 10001 stt && \
    useradd -r -u 10001 -g stt -d /tmp -s /usr/sbin/nologin stt && \
    mkdir -p /opt/models/stt && \
    chown -R stt:stt /opt/models/stt /app

USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "soorin_stt.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
