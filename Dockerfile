# API image for Cloudflare Containers (and any Docker host): runs cri.server unchanged.
#
#   docker build --platform linux/amd64 -t cri-api .
#   docker run -p 8080:8080 -e CRI_API_CORS_ORIGINS=http://localhost:3000 cri-api
#
# Only the package goes in: the SYNTHETIC review cluster is generated in memory and the
# travel resources and the open-data model ship inside src/cri/resources. Real data
# (data/raw) never enters the image (.dockerignore; CLAUDE.md rules 3-5).

# python:3.12-slim (numpy==1.26.2 has no 3.13 wheels), pinned by index digest.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install ".[api]" \
    && useradd --create-home --uid 10001 app

USER app
EXPOSE 8080
CMD ["uvicorn", "cri.server:app", "--host", "0.0.0.0", "--port", "8080"]
