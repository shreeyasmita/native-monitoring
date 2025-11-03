# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy your Python script into the container
COPY cloud_native_monitor.py .

# Install dependencies
RUN pip install psutil

# Set default command to run the monitor
CMD ["python", "cloud_native_monitor.py"]