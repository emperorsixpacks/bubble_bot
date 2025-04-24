# syntax=docker/dockerfile:1.4

# Set the python version as a build-time argument
ARG PYTHON_VERSION=3.13-slim-bullseye
FROM python:${PYTHON_VERSION} as base

# Stage 1: Install system dependencies with caching
FROM base as system-deps
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y \
    wget \
    # Required for wkhtmltoimage
    xfonts-75dpi \
    xfonts-base \
    gvfs \
    colord \
    glew-utils \
    libvisual-0.4-plugins \
    gstreamer1.0-tools \
    opus-tools \
    qt5-image-formats-plugins \
    qtwayland5 \
    qt5-qmltooling-plugins \
    librsvg2-bin \
    lm-sensors \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Install wkhtmltox with caching
FROM system-deps as wkhtml
RUN --mount=type=cache,target=/var/cache/apt \
    wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb \
    && dpkg -i wkhtmltox_0.12.6.1-2.bullseye_amd64.deb \
    && rm wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# Stage 3: Install Python environment
FROM wkhtml as python-env
WORKDIR /GitHub/bubble_bot

# Set Python-related environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/cache/uv

# Copy only requirements first for better caching

# Install uv and dependencies with cache

# Stage 4: Final image with application code
FROM python-env as runtime
COPY . .

# Clean up
RUN apt-get remove --purge -y \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /GitHub/bubble_bot
RUN --mount=type=cache,target=/cache/uv pip install --upgrade uv && uv sync
WORKDIR /GitHub/bubble_bot/src
CMD ["uv", "run", "utils.py"]
