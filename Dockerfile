FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the project's requirements
COPY requirement.txt ./

# Install minimal build tools and dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir -r requirement.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# First copy only the templates directory
COPY templates ./templates/

# Then copy the rest of the application code
COPY app.py ./

# Tell Flask which app to run and make it listen on 0.0.0.0
ENV FLASK_APP=app.py

EXPOSE 5000

CMD ["python", "app.py"]