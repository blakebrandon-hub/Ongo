# Use a minimal Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system-level dependencies
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

# Start the Flask server
CMD ["python", "app.py"]
