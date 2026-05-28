#!/bin/bash

echo "🎵 Spotify Playlist Downloader - Starting..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if [ ! -f "venv/.dependencies_installed" ]; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.dependencies_installed
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "   ⚠️  IMPORTANT: Edit .env and add your Spotify credentials!"
    echo "   Get them from: https://developer.spotify.com/dashboard"
    echo ""
    read -p "Press Enter after you've updated .env file..."
fi

echo ""
echo "✅ Starting Flask application..."
echo ""
echo "📍 Access the app at:"
echo "   - Local:   http://localhost:5000"
echo "   - Network: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "📊 Admin dashboard:"
echo "   - http://localhost:5000/admin"
echo "   - Protected with ADMIN_USERNAME / ADMIN_PASSWORD from .env"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "----------------------------------------"
echo ""

python3 app.py
