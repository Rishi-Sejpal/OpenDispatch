# OpenDispatch API image
# Production-ish single image: app + worker + scripts

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libgeos-dev \
        libproj-dev \
        libgdal-dev \
        libffi-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo \
        zlib1g \
        fonts-liberation \
        fonts-dejavu \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/opendispatch

# Install python deps first for cache friendliness
COPY apps/api/pyproject.toml /srv/opendispatch/pyproject.toml
RUN pip install --upgrade pip \
    && pip install \
        fastapi==0.115.5 \
        'uvicorn[standard]==0.32.1' \
        pydantic==2.10.2 \
        pydantic-settings==2.6.1 \
        sqlalchemy==2.0.36 \
        alembic==1.14.0 \
        'psycopg[binary]==3.2.3' \
        geoalchemy2==0.16.0 \
        shapely==2.0.6 \
        redis==5.2.0 \
        celery==5.4.0 \
        'python-jose[cryptography]==3.3.0' \
        'passlib[argon2]==1.7.4' \
        argon2-cffi==23.1.0 \
        python-multipart==0.0.20 \
        email-validator==2.2.0 \
        httpx==0.28.0 \
        jinja2==3.1.4 \
        weasyprint==63.1 \
        structlog==24.4.0 \
        pyyaml==6.0.2 \
        numpy==2.2.0 \
        pytest==8.3.4 \
        pytest-asyncio==0.24.0 \
        pytest-cov==6.0.0 \
        ruff==0.8.1 \
        mypy==1.13.0 \
        faker==33.0.0 \
        freezegun==1.5.1 \
    && pip check

# Copy app code
COPY apps/api /srv/opendispatch/apps/api
COPY services /srv/opendispatch/services
COPY packages /srv/opendispatch/packages
COPY data /srv/opendispatch/data

ENV PYTHONPATH=/srv/opendispatch:/srv/opendispatch/apps/api:/srv/opendispatch/services:/srv/opendispatch/packages

# Make the project importable as `app`
WORKDIR /srv/opendispatch/apps/api
RUN ls -la

EXPOSE 8000

# Default command: run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
