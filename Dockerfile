# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Make script executable
RUN chmod +x server.py

# Set environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1

# Run the MCP server
# Note: This expects stdio communication, so it needs to be run with -i flag
CMD ["python3", "server.py"]
