Use official Python base image
FROM python:3.11-slim
Set working directory
WORKDIR /app
Copy your Python script into the container
COPY app.py .
Install dependencies
RUN pip install psutil
Set default command to run the monitor
CMD ["python", "app.py"]
# Expose port
EXPOSE 5000