# syntax=docker/dockerfile:1
# ---- Insurance Claims API image ----
FROM python:3.13-slim

# Faster, cleaner Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY app ./app

# The log directory is written at runtime.
RUN mkdir -p logs

EXPOSE 8000

# Bind to 0.0.0.0 so the service is reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
