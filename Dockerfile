# Set the python version as a build-time argument
# with Python 3.12 as the default
ARG PYTHON_VERSION=3.12-slim-bullseye
FROM python:${PYTHON_VERSION}

RUN pip install --upgrade uv

# Set Python-related environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install os dependencies for our mini vm
RUN apt-get update && apt-get install -y \
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

RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

RUN dpkg -i wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# Create the mini vm's code directory
RUN mkdir -p /GitHub/bubble_bot

# Set the working directory to that same code directory
WORKDIR /GitHub/bubble_bot/src

# Copy the requirements file into the container

# copy the project code into the container's working directory
COPY . /GitHub/bubble_bot

RUN uv sync

# Clean up apt cache to reduce image size
RUN apt-get remove --purge -y \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

CMD uv run utils.py 
