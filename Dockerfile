# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Development image: pinned dev tools, sources and tests. Used by CI for lint, types and tests.
FROM base AS test
COPY requirements-lock.txt ./
RUN pip install -r requirements-lock.txt
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY tests ./tests
COPY examples ./examples
RUN pip install --no-deps -e .
CMD ["pytest", "--cov", "--cov-report=term"]

# Runtime image: the package with pinned runtime dependencies, run as a non-root user.
FROM base AS runtime
LABEL org.opencontainers.image.source="https://github.com/nurzhvn52/reteval" \
      org.opencontainers.image.licenses="MIT"
ENV MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib
COPY requirements-lock.txt pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install -c requirements-lock.txt . && rm -rf src
COPY examples ./examples
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin reteval
USER 10001
ENTRYPOINT ["reteval"]
CMD ["--help"]
