# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY main.py .
COPY config.yaml .
COPY modules/ ./modules/
COPY utils/ ./utils/

# Create cache directory and set ownership
RUN mkdir -p .cache && \
    chown -R appuser:appuser /app /home/appuser/.local

# Switch to non-root user
USER appuser

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Set default command
ENTRYPOINT ["python", "main.py"]
CMD ["--config", "config.yaml"]
