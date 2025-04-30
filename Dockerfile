# syntax=docker/dockerfile:1.4
ARG PYTHON_VERSION=3.13-slim-bullseye
FROM python:${PYTHON_VERSION} as base
ENV DOCKER_BUILDKIT=1

# Stage 1: Install minimal system dependencies for Chromium
FROM base as system-deps
RUN --mount=type=cache,id=s/acffad2a-9b32-43e8-89be-d741991f4423-/var/cache/apt,target=/var/cache/apt \
    apt-get update && apt-get install -y \
    wget \
    libglib2.0-0 \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libxcomposite1 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libxss1 \
    fonts-liberation \
    libasound2 \
    libxdamage1 \
    libxtst6 \
    libx11-xcb1 \
    libcups2 \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Install Playwright and Chromium
FROM system-deps as playwright
WORKDIR /GitHub/bubble_bot
COPY pyproject.toml uv.lock ./
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/var/cache/uv

# Install uv to manage Playwright installation
RUN --mount=type=cache,id=s/acffad2a-9b32-43e8-89be-d741991f4423-${UV_CACHE_DIR},target=${UV_CACHE_DIR} \
    pip install --upgrade uv

# Install Playwright and Chromium
RUN --mount=type=cache,id=s/acffad2a-9b32-43e8-89be-d741991f4423-/root/.cache/playwright,target=/root/.cache/playwright \
    uv add playwright && \
    uv run playwright install-deps && \
    uv run playwright install chromium

# Stage 3: Sync project Python dependencies
FROM playwright as build
RUN --mount=type=cache,id=s/acffad2a-9b32-43e8-89be-d741991f4423-${UV_CACHE_DIR},target=${UV_CACHE_DIR} \
    uv sync

# Stage 4: Final runtime image
FROM build as runtime
COPY . .
#RUN rm -rf .venv  
ENV TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
    IBM_API_KEY=$IBM_API_KEY \
    IBM_BUCKET_NAME=$IBM_BUCKET_NAME \
    IBM_BUCKET_INSTANCE_ID=$IBM_BUCKET_INSTANCE_ID \
    IBM_SERVICE_ENDPOINT=$IBM_SERVICE_ENDPOINT \
    COIN_GECKO_API_KEY=$COIN_GECKO_API_KEY \
WORKDIR /GitHub/bubble_bot/src
CMD ["uv", "run", "bot.py"]

