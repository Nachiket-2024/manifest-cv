# Compiles native extensions into a venv so build tools never ship in the
# runtime image.
FROM python:3.14.6-slim AS builder

WORKDIR /app

# gcc + libpq-dev: needed to compile packages with native extensions
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install into an isolated venv so the runtime stage can copy it wholesale
# without dragging along build-only files pip leaves in site-packages.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Slim final image with only the interpreter, runtime libraries, venv, and app
# source.
FROM python:3.14.6-slim

WORKDIR /app

# libpq5: runtime Postgres client library asyncpg/psycopg need to connect;
# libpq-dev (headers) isn't needed here. No pg_isready: Postgres readiness
# is checked via docker-compose's healthcheck on the postgres service itself.
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# tectonic: self-contained LaTeX engine (ManifestCV. See
# document_generation/tectonic_compiler.py) used to compile generated
# resumes to PDF. Installed as a static binary rather than full texlive
# (several GB). The musl build specifically, since it's fully statically
# linked (unlike the gnu build, which dynamically links libgraphite2,
# libharfbuzz, etc. That this slim base image doesn't ship, and fails at
# runtime with "error while loading shared libraries"). Ca-certificates is
# kept (not just a build-time need. Every other outbound HTTPS call this
# backend makes, e.g. to Gemini, needs it too). Only curl itself is removed
# once the download is done. Tectonic fetches the actual LaTeX format
# bundle it needs over the network on first compile, caching it under
# $HOME/.cache/Tectonic (the "app" user's home is /app, already owned by
# app:app below). The sha256sum check pins the exact release asset. HTTPS
# alone only protects the transport, not against a compromised/replaced
# release asset at the source. A version bump means recomputing this hash
# (`curl -fsSL <url> | sha256sum`) deliberately, not just editing the URL.
RUN apt-get update && apt-get install -y curl ca-certificates \
    && curl -fsSL https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.16.9/tectonic-0.16.9-x86_64-unknown-linux-musl.tar.gz -o /tmp/tectonic.tar.gz \
    && echo "60b13a0826ae7ad9ce34b4a2df06bff2cfcfa6dda8a915477c0cbb84e1a4a902  /tmp/tectonic.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tectonic.tar.gz -C /usr/local/bin \
    && rm /tmp/tectonic.tar.gz \
    && apt-get purge -y curl && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/ .

# backend, taskiq_worker, and alembic share this image and do not need root at
# runtime. /app/logs is created during the build so the dev named volume mounted
# there inherits ownership that the non-root app user can write to.
RUN mkdir -p /app/logs \
    && groupadd --system app && useradd --system --gid app --home-dir /app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Fallback healthcheck for running this image outside Compose. Compose defines
# the service healthcheck that gates dependent service startup.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')" || exit 1

# Overridden in docker-compose for the taskiq_worker and alembic services
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
