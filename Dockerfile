# Adobe-compliant Dockerfile — single stage, CPU-only, no internet needed at runtime
FROM --platform=linux/amd64 python:3.9-slim-bookworm

# Working directory inside the container
WORKDIR /app

# Install required system packages for PyMuPDF (fitz) to work
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Entry point — runs your extraction script when container starts
CMD ["python", "extract_outline.py"]
