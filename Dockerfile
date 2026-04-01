# Stage 1: Build React UI
FROM node:20-slim as frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
# This drops the output into /app/dashboard/ui (per vite.config.ts)
RUN npm run build

# Stage 2: Build Python Packages
FROM python:3.11-slim as backend-builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final Production Container
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN mkdir -p /app/data

# Copy python dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy python source code
COPY . .

# Copy compiled React UI from Node stage to Flask's static handler
COPY --from=frontend-builder /app/dashboard/ui /app/dashboard/ui

# Clean up raw node source code taking up space
RUN rm -rf frontend

# Startup command pointing to Procfile
CMD ["honcho", "start"]
