FROM python:3.14.4-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_PYTHON_DOWNLOADS=never
ENV GWN_MQTT_CONTAINER=true

RUN apk add --no-cache ca-certificates \
    build-base \
    linux-headers \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./

# Install dependencies only.
RUN uv sync --frozen --no-dev --no-install-project --python /usr/local/bin/python3

COPY gwn ./gwn
COPY mqtt ./mqtt

RUN uv sync --frozen --no-dev --python /usr/local/bin/python3

VOLUME ["/config"]

CMD ["gwn_mqtt", "--config_path", "/config/config.yml"]
