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

# Check if admin user exists
echo "👤 Checking for admin user..."
python3 -c "import database as db; import sys; conn = db.get_db(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1'); count = cursor.fetchone()[0]; conn.close(); sys.exit(0 if count > 0 else 1)" 2>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  No admin user found!"
    echo "   Let's create one now..."
    echo ""
    python3 create_admin.py
    echo ""
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
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "----------------------------------------"
echo ""

python3 app.py
