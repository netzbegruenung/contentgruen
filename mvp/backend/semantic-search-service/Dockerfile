FROM python:3.13-slim

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

# Das NLI-Modell der NLI-Stufe (#387, core/config.py NLI_MODELL), ebenso vorgeladen
RUN python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
    name = 'MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7'; \
    AutoTokenizer.from_pretrained(name); AutoModelForSequenceClassification.from_pretrained(name); \
    print('NLI model pre-downloaded successfully')"

# Nicht im Image: der Bestaetiger (core/config.py NLI_BESTAETIGER_MODELL, rund 2,2 GB),
# standardmaessig aus. Er machte jedes Image gut doppelt so gross und fuellte die Registry
# (14.11.). Wer ihn einschaltet, laesst ihn beim Start laden (CONFIG.md,
# SEMANTIC_SEARCH_NLI_BESTAETIGER).

# Ab hier nur noch die eingebauten Modelle: Ohne Offline-Modus fragt der Dienst bei
# jedem Start huggingface.co an (Startzeit, Datenverkehr in die USA) und koennte eine
# neuere Modellrevision ziehen als die, die der Nachtlauf misst. Erst nach den
# Vorlade-Schritten, damit der Build die Modelle noch herunterladen kann (#578).
# Ein neues Modell gehoert oben in einen Vorlade-Schritt (docs/CI.md, "Model cache").
ENV HF_HUB_OFFLINE=1

# Copy application code - adjusted path for mvp context
COPY backend/semantic-search-service/app /app

# Copy backup/restore scripts into the image
COPY scripts/backup /scripts/backup
RUN chmod +x /scripts/backup/*.sh

# SQL-Migrationen, die der Dienst beim Start einspielt (infrastructure/database/migrationen.py)
COPY backend/postgres-app/migrations /migrations

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

# Ein Worker ist Absicht: Die Rate-Limiter (utils/rate_limiter.py) und die Sperre
# je Suchtext (services/search/search_query_statement.py) leben im Prozessspeicher.
# Mit --workers N haette jeder Prozess eigene Zaehler und Sperren - die Limits
# wuerden sich ver-N-fachen, und gleichzeitige gleiche Suchen koennten wieder
# doppelte Aussagen anlegen. Ebenso die Meilenstein-Abzeichen
# (services/abzeichen_service.py): Ein Nein oder ein Widerruf wirkte sonst nur im
# Prozess, der die Anfrage bekam, in den anderen bis zu 15 Minuten nicht.
# Wer skaliert, braucht dafuer einen geteilten Speicher.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
