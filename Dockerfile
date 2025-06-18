FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variable for Python path
ENV PYTHONPATH=/app

# Expose port 8000
EXPOSE 8000

# Run the server in Streamable HTTP mode (recommended for Docker)
CMD ["python", "start_server.py", "--http"]
