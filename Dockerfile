FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (including web directory)
COPY . .

# Ensure web directory exists and has proper permissions
RUN mkdir -p /app/web && chmod -R 755 /app/web

# Set environment variable for Python path
ENV PYTHONPATH=/app

# Expose port 8000
EXPOSE 8000

# Run the server in Streamable HTTP mode (recommended for Docker)
CMD ["python", "start_server.py", "--http"]
