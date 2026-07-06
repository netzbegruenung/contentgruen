FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory early
WORKDIR /app

# Install dependencies - adjusted path for mvp context
COPY backend/semantic-search-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn[standard]

# Pre-download the E5 multilingual model during build
# This prevents re-downloading on every container start
RUN python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('intfloat/multilingual-e5-base'); \
    print('E5 multilingual model pre-downloaded successfully')"

# Copy application code - adjusted path for mvp context
COPY backend/semantic-search-service/app /app

# Copy backup/restore scripts into the image
COPY scripts/backup /scripts/backup
RUN chmod +x /scripts/backup/*.sh

# Copy seed data into the image
COPY data /data

# Create directories for volume mount points
# These must exist before Docker tries to mount volumes to them
RUN mkdir -p /var/log /metadata /backups

# Set environment variables for containerized environment
ENV DOCKER_CONTAINER=true
# Don't hardcode paths here - let docker-compose set them
# ENV SEMANTIC_SEARCH_DATA_PATH=/data/seed/v1.0
# ENV SEMANTIC_SEARCH_METADATA_PATH=/metadata

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
