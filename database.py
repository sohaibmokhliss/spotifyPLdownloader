import sqlite3

DATABASE_PATH = "app.db"


def get_db():
    """Get a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the minimal tables used by the public app."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS download_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            download_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            playlist_url TEXT,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


def log_activity(action, details=None, ip_address=None):
    """Store a minimal activity record keyed by visitor IP."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO activity_logs (action, details, ip_address) VALUES (?, ?, ?)",
        (action, details, ip_address),
    )

    conn.commit()
    conn.close()


def log_download(
    download_type,
    item_name,
    playlist_url=None,
    success=True,
    error_message=None,
    ip_address=None,
):
    """Store a download record keyed by visitor IP."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO download_history (
            download_type,
            item_name,
            playlist_url,
            success,
            error_message,
            ip_address
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (download_type, item_name, playlist_url, success, error_message, ip_address),
    )

    conn.commit()
    conn.close()


def get_recent_activity(limit=50):
    """Get recent activity logs without user joins."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, action, details, ip_address, timestamp
        FROM activity_logs
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )

    activities = cursor.fetchall()
    conn.close()
    return [dict(activity) for activity in activities]


def get_download_history(limit=50):
    """Get recent download history without user joins."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, download_type, item_name, playlist_url, success, error_message, ip_address, timestamp
        FROM download_history
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )

    downloads = cursor.fetchall()
    conn.close()
    return [dict(download) for download in downloads]


def get_stats():
    """Get dashboard statistics for the public IP-based logging view."""
    conn = get_db()
    cursor = conn.cursor()
    stats = {}

    cursor.execute("SELECT COUNT(*) AS count FROM download_history WHERE success = 1")
    stats["total_downloads"] = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM download_history WHERE success = 0")
    stats["failed_downloads"] = cursor.fetchone()["count"]

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM activity_logs
        WHERE timestamp > datetime('now', '-1 day')
        """
    )
    stats["activity_last_24h"] = cursor.fetchone()["count"]

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM download_history
        WHERE timestamp > datetime('now', '-1 day')
        """
    )
    stats["downloads_last_24h"] = cursor.fetchone()["count"]

    cursor.execute(
        """
        SELECT COUNT(DISTINCT ip_address) AS count
        FROM (
            SELECT ip_address
            FROM activity_logs
            WHERE ip_address IS NOT NULL AND ip_address != ''
            UNION
            SELECT ip_address
            FROM download_history
            WHERE ip_address IS NOT NULL AND ip_address != ''
        )
        """
    )
    stats["unique_ips"] = cursor.fetchone()["count"]

    conn.close()
    return stats


init_db()
