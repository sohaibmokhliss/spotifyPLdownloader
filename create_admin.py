#!/usr/bin/env python3
"""
Create an admin user for the Spotify Playlist Downloader
"""
import sqlite3
import hashlib

DATABASE_PATH = 'app.db'

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user():
    print("=== Create Admin User ===\n")
    
    username = input("Enter admin username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return
    
    password = input("Enter admin password (min 6 characters): ").strip()
    if len(password) < 6:
        print("❌ Password must be at least 6 characters")
        return
    
    email = input("Enter admin email (optional): ").strip()
    email = email if email else None
    
    # Create database connection
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)',
            (username, password_hash, email, True)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        print(f"\n✅ Admin user created successfully!")
        print(f"   Username: {username}")
        print(f"   User ID: {user_id}")
        print(f"\nYou can now:")
        print(f"   1. Start the app: python app.py")
        print(f"   2. Login at: http://localhost:5000/login")
        print(f"   3. Access admin dashboard at: http://localhost:5000/admin")
    except sqlite3.IntegrityError:
        print(f"\n❌ Failed to create admin user. Username '{username}' already exists.")
    finally:
        conn.close()

if __name__ == '__main__':
    create_admin_user()
