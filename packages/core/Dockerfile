FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package
COPY . .

# Install package in development mode
RUN pip install -e .

# Create data and outputs directories
RUN mkdir -p /data /outputs

# Default command
CMD ["python", "-m", "signalops.cli", "--help"]
