#!/bin/bash

# Content Crew Prodigal API - Production Startup Script

echo "🚀 Starting Content Crew Prodigal API in Production Mode"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please copy env.production.template to .env and configure it."
    echo "   cp env.production.template .env"
    exit 1
fi

# Start the application
echo "🌟 Starting production server..."
python main.py
