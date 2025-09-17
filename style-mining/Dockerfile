FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing and OCR
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    libopencv-dev \
    python3-opencv \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make main script executable
RUN chmod +x src/main.py

# Default command
CMD ["python", "src/main.py", "--help"]