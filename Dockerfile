# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create dedicated directory for SQLite data
RUN mkdir -p /app/data

# Copy installed dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY . .

# Expose Dashboard port
EXPOSE 5000

# Default command uses Honcho to run both web and worker from Procfile
CMD ["honcho", "start"]
