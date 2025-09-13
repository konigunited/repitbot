#!/bin/bash

# Simple deployment script for RepitBot
# Usage: ./deploy-simple.sh

set -e

echo "🚀 Starting RepitBot deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data logs charts

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration before continuing."
    echo "   Especially set TELEGRAM_TOKEN and ADMIN_ACCESS_CODE"
    read -p "Press Enter after editing .env file..."
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start containers
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check container status
echo "📊 Checking container status..."
docker-compose ps

# Show logs
echo "📋 Showing recent logs..."
docker-compose logs --tail=20

echo "✅ Deployment completed!"
echo ""
echo "📝 Useful commands:"
echo "  View logs:           docker-compose logs -f"
echo "  Stop bot:           docker-compose down"
echo "  Restart bot:        docker-compose restart"
echo "  Update bot:         git pull && docker-compose build && docker-compose up -d"
echo "  Enter container:    docker-compose exec repitbot bash"
echo ""
echo "🔍 Check bot status: docker-compose ps"