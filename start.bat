@echo off
echo ========================================
echo  Spotify Playlist Downloader
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
if not exist "venv\.dependencies_installed" (
    echo Installing dependencies...
    pip install -r requirements.txt
    type nul > venv\.dependencies_installed
)

REM Check if .env exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env and add your Spotify credentials!
    echo Get them from: https://developer.spotify.com/dashboard
    echo.
    pause
)

REM Check for admin user
echo Checking for admin user...
python -c "import database as db; import sys; conn = db.get_db(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1'); count = cursor.fetchone()[0]; conn.close(); sys.exit(0 if count > 0 else 1)" 2>nul

if errorlevel 1 (
    echo.
    echo No admin user found!
    echo Let's create one now...
    echo.
    python create_admin.py
    echo.
)

echo.
echo ========================================
echo Starting Flask application...
echo ========================================
echo.
echo Access the app at:
echo   - Local:  http://localhost:5000
echo   - Admin:  http://localhost:5000/admin
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
