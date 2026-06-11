FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Prisma
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY global_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY global_server/ ./global_server/
COPY shared/ ./shared/
COPY prisma/ ./prisma/

# Set Python path
ENV PYTHONPATH=/app

# Generate Prisma client
RUN prisma generate

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "global_server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
