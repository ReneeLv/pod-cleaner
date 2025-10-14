# Multi-stage build for Pod Cleaner
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r podcleaner && useradd -r -g podcleaner podcleaner

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/podcleaner/.local

# Copy application code
COPY src/ ./src/

# Set Python path
ENV PATH=/home/podcleaner/.local/bin:$PATH
ENV PYTHONPATH=/app

# Change ownership to non-root user
RUN chown -R podcleaner:podcleaner /app

# Switch to non-root user
USER podcleaner

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import kubernetes; print('Healthy')" || exit 1

# Default environment variables
ENV IN_CLUSTER=true
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json
ENV RUN_INTERVAL_MINUTES=10
ENV EXCLUDED_NAMESPACES=kube-system,kube-public,kube-node-lease
ENV HEALTHY_POD_STATES=Running,Init

# Run the application
CMD ["python", "-m", "src.main"]
