import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

DATABASE_PATH = 'app.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with required tables"""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Activity logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Download history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS download_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            download_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            playlist_url TEXT,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email=None, is_admin=False):
    """Create a new user"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)',
            (username, password_hash, email, is_admin)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def verify_user(username, password):
    """Verify user credentials"""
    conn = get_db()
    cursor = conn.cursor()

    password_hash = hash_password(password)
    cursor.execute(
        'SELECT * FROM users WHERE username = ? AND password_hash = ?',
        (username, password_hash)
    )
    user = cursor.fetchone()
    conn.close()

    return dict(user) if user else None

def create_session(user_id, ip_address, user_agent):
    """Create a new session for user"""
    conn = get_db()
    cursor = conn.cursor()

    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)

    cursor.execute(
        'INSERT INTO sessions (user_id, session_token, ip_address, user_agent, expires_at) VALUES (?, ?, ?, ?, ?)',
        (user_id, session_token, ip_address, user_agent, expires_at)
    )

    # Update last login
    cursor.execute(
        'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
        (user_id,)
    )

    conn.commit()
    conn.close()

    return session_token

def get_session(session_token):
    """Get session by token"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.*, u.username, u.is_admin
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
    ''', (session_token,))

    session = cursor.fetchone()
    conn.close()

    return dict(session) if session else None

def delete_session(session_token):
    """Delete a session (logout)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
    conn.commit()
    conn.close()

def log_activity(user_id, action, details=None, ip_address=None, user_agent=None):
    """Log user activity"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO activity_logs (user_id, action, details, ip_address, user_agent) VALUES (?, ?, ?, ?, ?)',
        (user_id, action, details, ip_address, user_agent)
    )

    conn.commit()
    conn.close()

def log_download(user_id, download_type, item_name, playlist_url=None, success=True, error_message=None, ip_address=None):
    """Log download activity"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO download_history (user_id, download_type, item_name, playlist_url, success, error_message, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, download_type, item_name, playlist_url, success, error_message, ip_address)
    )

    conn.commit()
    conn.close()

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    return dict(user) if user else None

# Authentication decorator
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')

        if not session_token:
            return jsonify({'error': 'Authentication required'}), 401

        session = get_session(session_token)
        if not session:
            return jsonify({'error': 'Invalid or expired session'}), 401

        # Add user info to request
        request.user = session
        return f(*args, **kwargs)

    return decorated_function

# Admin-only decorator
def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')

        if not session_token:
            return jsonify({'error': 'Authentication required'}), 401

        session = get_session(session_token)
        if not session or not session['is_admin']:
            return jsonify({'error': 'Admin privileges required'}), 403

        request.user = session
        return f(*args, **kwargs)

    return decorated_function

# Admin statistics functions
def get_all_users():
    """Get all users with stats"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            u.id,
            u.username,
            u.email,
            u.is_admin,
            u.created_at,
            u.last_login,
            COUNT(DISTINCT dh.id) as total_downloads,
            COUNT(DISTINCT al.id) as total_activities
        FROM users u
        LEFT JOIN download_history dh ON u.id = dh.user_id
        LEFT JOIN activity_logs al ON u.id = al.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''')

    users = cursor.fetchall()
    conn.close()

    return [dict(user) for user in users]

def get_recent_activity(limit=50):
    """Get recent activity logs"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            al.*,
            u.username
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.timestamp DESC
        LIMIT ?
    ''', (limit,))

    activities = cursor.fetchall()
    conn.close()

    return [dict(activity) for activity in activities]

def get_download_history(limit=50):
    """Get recent download history"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            dh.*,
            u.username
        FROM download_history dh
        LEFT JOIN users u ON dh.user_id = u.id
        ORDER BY dh.timestamp DESC
        LIMIT ?
    ''', (limit,))

    downloads = cursor.fetchall()
    conn.close()

    return [dict(download) for download in downloads]

def get_stats():
    """Get overall system statistics"""
    conn = get_db()
    cursor = conn.cursor()

    stats = {}

    # Total users
    cursor.execute('SELECT COUNT(*) as count FROM users')
    stats['total_users'] = cursor.fetchone()['count']

    # Total downloads
    cursor.execute('SELECT COUNT(*) as count FROM download_history WHERE success = 1')
    stats['total_downloads'] = cursor.fetchone()['count']

    # Failed downloads
    cursor.execute('SELECT COUNT(*) as count FROM download_history WHERE success = 0')
    stats['failed_downloads'] = cursor.fetchone()['count']

    # Active sessions
    cursor.execute('SELECT COUNT(*) as count FROM sessions WHERE expires_at > CURRENT_TIMESTAMP')
    stats['active_sessions'] = cursor.fetchone()['count']

    # Downloads by type
    cursor.execute('''
        SELECT download_type, COUNT(*) as count
        FROM download_history
        WHERE success = 1
        GROUP BY download_type
    ''')
    stats['downloads_by_type'] = {row['download_type']: row['count'] for row in cursor.fetchall()}

    # Recent activity count (last 24 hours)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM activity_logs
        WHERE timestamp > datetime('now', '-1 day')
    ''')
    stats['activity_last_24h'] = cursor.fetchone()['count']

    # Top users by downloads
    cursor.execute('''
        SELECT u.username, COUNT(*) as download_count
        FROM download_history dh
        JOIN users u ON dh.user_id = u.id
        WHERE dh.success = 1
        GROUP BY u.id
        ORDER BY download_count DESC
        LIMIT 5
    ''')
    stats['top_users'] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return stats

def get_user_activity(user_id, limit=50):
    """Get activity for a specific user"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM activity_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (user_id, limit))

    activities = cursor.fetchall()
    conn.close()

    return [dict(activity) for activity in activities]

def get_user_downloads(user_id, limit=50):
    """Get downloads for a specific user"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM download_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (user_id, limit))

    downloads = cursor.fetchall()
    conn.close()

    return [dict(download) for download in downloads]

# Initialize database when module is imported
init_db()
