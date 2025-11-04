#!/bin/bash

echo "🐳 Building Docker image..."
docker-compose build

echo "🚀 Starting container..."
docker-compose up -d

echo "⏳ Waiting for container to be ready..."
sleep 5

echo "✅ Testing health endpoint..."
curl -f http://localhost:5000/health

echo ""
echo "🎉 Deployment complete!"
echo "📊 Access the monitor at: http://localhost:5000"
echo "📝 View logs: docker-compose logs -f"