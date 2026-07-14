FROM python:3.11-slim

# System deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# pip cache mount: downloaded wheels are reused on subsequent builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .

# Persistent directories — all overridden by volume mounts at runtime
RUN mkdir -p /app/models/detectors /app/models/reid \
             /app/zones \
             /app/videos

ENV MODELS_DIR=/app/models
ENV ZONES_DIR=/app/zones
ENV VIDEOS_DIR=/app/videos
ENV API_KEYS_FILE=/app/api_keys.json
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
