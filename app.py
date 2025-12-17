import database as db
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import os
import re
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import time
from youtubesearchpython import VideosSearch
import yt_dlp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())

# Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'youtube-to-mp315.p.rapidapi.com')
DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', 'downloads')
ALLOW_SERVER_STORAGE = os.getenv('ALLOW_SERVER_STORAGE', 'false').lower() == 'true'

# Create downloads folder
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Global progress tracker
download_progress = {
    'current': 0,
    'total': 0,
    'current_track': '',
    'status': 'idle',
    'completed': [],
    'failed': [],
    'should_stop': False,
    'playlist_name': '',
    'playlist_url': '',
    'tracks_info': []
}

def get_spotify_client():
    """Initialize Spotify client"""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise Exception("Spotify credentials not configured")
    
    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def extract_playlist_id(playlist_url):
    """Extract playlist ID from Spotify URL"""
    # Handle different URL formats
    if 'open.spotify.com/playlist/' in playlist_url:
        playlist_id = playlist_url.split('playlist/')[1].split('?')[0]
    elif 'spotify:playlist:' in playlist_url:
        playlist_id = playlist_url.split('spotify:playlist:')[1]
    else:
        playlist_id = playlist_url
    
    return playlist_id

def sanitize_filename(filename):
    """Clean filename for safe file system storage"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    filename = filename[:200]
    return filename.strip()

@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get app configuration"""
    return jsonify({
        'allow_server_storage': ALLOW_SERVER_STORAGE
    })

@app.route('/api/playlist/info', methods=['POST'])
def get_playlist_info():
    """Get playlist metadata"""
    try:
        data = request.get_json()
        playlist_url = data.get('playlist_url')
        
        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400
        
        sp = get_spotify_client()
        playlist_id = extract_playlist_id(playlist_url)
        
        # Get playlist details
        playlist = sp.playlist(playlist_id)
        
        tracks_info = []
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        
        # Handle pagination
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        for item in tracks:
            if item['track']:
                track = item['track']
                tracks_info.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                    'album': track['album']['name'] if track['album'] else 'Unknown'
                })
        
        return jsonify({
            'success': True,
            'playlist': {
                'name': playlist['name'],
                'description': playlist['description'],
                'track_count': len(tracks_info),
                'image': playlist['images'][0]['url'] if playlist['images'] else None,
                'tracks': tracks_info
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def search_youtube_video(song_name, artist):
    """Find best matching YouTube video"""
    try:
        query = f"{song_name} {artist} official audio"
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        
        if results['result']:
            video_id = results['result'][0]['id']
            return f"https://www.youtube.com/watch?v={video_id}"
        
        # Fallback without "official audio"
        query = f"{song_name} {artist}"
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        
        if results['result']:
            video_id = results['result'][0]['id']
            return f"https://www.youtube.com/watch?v={video_id}"
        
        return None
    
    except Exception as e:
        print(f"YouTube search error: {e}")
        return None

def download_from_youtube(youtube_url, artist, track_name, download_folder=DOWNLOAD_FOLDER, format_type='mp3'):
    """Download MP3 or MP4 using yt-dlp"""
    try:
        filename = sanitize_filename(f"{artist} - {track_name}")
        filepath = os.path.join(download_folder, filename)

        # Configure yt-dlp options based on format
        if format_type == 'mp4':
            # Download video (MP4)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': filepath,
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
            }
        else:
            # Download audio only (MP3)
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': filepath,
                'quiet': True,
                'no_warnings': True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        return True

    except Exception as e:
        print(f"Download error for {artist} - {track_name}: {e}")
        return False

@app.route('/api/download', methods=['POST'])
def download_playlist():
    """Start download process"""
    global download_progress

    try:
        data = request.get_json()
        playlist_url = data.get('playlist_url')
        resume = data.get('resume', False)
        download_to_device = data.get('download_to_device', False)
        format_type = data.get('format', 'mp3')  # Default to mp3

        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400

        sp = get_spotify_client()
        playlist_id = extract_playlist_id(playlist_url)

        # Get playlist details
        playlist = sp.playlist(playlist_id)
        playlist_name = sanitize_filename(playlist['name'])

        # Choose download location
        if download_to_device:
            import tempfile
            playlist_folder = tempfile.mkdtemp()
        else:
            playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_name)
            os.makedirs(playlist_folder, exist_ok=True)

        # Get all tracks
        tracks_info = []
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']

        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        for item in tracks:
            if item['track']:
                track = item['track']
                tracks_info.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown'
                })

        # If not resuming, reset progress
        if not resume:
            download_progress = {
                'current': 0,
                'total': len(tracks_info),
                'current_track': '',
                'status': 'downloading',
                'completed': [],
                'failed': [],
                'should_stop': False,
                'playlist_name': playlist_name,
                'playlist_url': playlist_url,
                'tracks_info': tracks_info
            }
        else:
            # Resuming - keep existing progress but reset stop flag
            download_progress['should_stop'] = False
            download_progress['status'] = 'downloading'

        # Download each track
        start_index = download_progress['current'] if resume else 0

        for idx in range(start_index, len(tracks_info)):
            # Check if should stop
            if download_progress['should_stop']:
                download_progress['status'] = 'paused'
                return jsonify({
                    'success': True,
                    'message': 'Download paused',
                    'completed': len(download_progress['completed']),
                    'failed': len(download_progress['failed']),
                    'paused': True
                })

            track = tracks_info[idx]
            download_progress['current'] = idx + 1
            download_progress['current_track'] = f"{track['artist']} - {track['name']}"

            # Check if already downloaded
            track_name = f"{track['artist']} - {track['name']}"
            if track_name in download_progress['completed']:
                continue

            # Search YouTube
            youtube_url = search_youtube_video(track['name'], track['artist'])

            if not youtube_url:
                download_progress['failed'].append({
                    'track': track_name,
                    'reason': 'YouTube video not found'
                })
                continue

            # Download from YouTube to playlist folder
            success = download_from_youtube(youtube_url, track['artist'], track['name'], playlist_folder, format_type)

            if success:
                download_progress['completed'].append(track_name)
                # Log successful download
                session_token = request.cookies.get('session_token')
                session = db.get_session(session_token) if session_token else None
                if session:
                    db.log_download(session['user_id'], 'playlist', track_name, playlist_url, True, None, request.remote_addr)
            else:
                download_progress['failed'].append({
                    'track': track_name,
                    'reason': 'Download failed'
                })
                # Log failed download
                session_token = request.cookies.get('session_token')
                session = db.get_session(session_token) if session_token else None
                if session:
                    db.log_download(session['user_id'], 'playlist', track_name, playlist_url, False, 'Download failed', request.remote_addr)

            # Small delay to avoid rate limits
            time.sleep(1)

        download_progress['status'] = 'completed'

        if download_to_device:
            # Create ZIP file and send to client
            import zipfile
            import tempfile
            import shutil

            zip_path = os.path.join(tempfile.gettempdir(), f'{playlist_name}.zip')

            file_extension = '.mp4' if format_type == 'mp4' else '.mp3'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(playlist_folder):
                    for file in files:
                        if file.endswith(file_extension):
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, file)

            response = send_from_directory(
                os.path.dirname(zip_path),
                os.path.basename(zip_path),
                as_attachment=True,
                download_name=f'{playlist_name}.zip'
            )

            # Clean up temp files after sending
            @response.call_on_close
            def cleanup():
                try:
                    shutil.rmtree(playlist_folder)
                    os.remove(zip_path)
                except:
                    pass

            return response
        else:
            return jsonify({
                'success': True,
                'message': f"Downloaded {len(download_progress['completed'])} of {download_progress['total']} tracks",
                'completed': len(download_progress['completed']),
                'failed': len(download_progress['failed'])
            })

    except Exception as e:
        download_progress['status'] = 'error'
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get download progress"""
    return jsonify(download_progress)

@app.route('/api/stop', methods=['POST'])
def stop_download():
    """Stop the current download"""
    global download_progress
    download_progress['should_stop'] = True
    return jsonify({'success': True, 'message': 'Download will stop after current track'})

@app.route('/api/resume', methods=['POST'])
def resume_download():
    """Resume a paused download"""
    global download_progress

    if download_progress['status'] != 'paused':
        return jsonify({'error': 'No paused download to resume'}), 400

    # Call download with resume flag
    return download_playlist()

@app.route('/api/youtube/download', methods=['POST'])
def download_youtube_direct():
    """Download a single YouTube video directly to downloads folder or send to client"""
    # Get current user
    session_token = request.cookies.get("session_token")
    session = db.get_session(session_token) if session_token else None
    user_id = session["user_id"] if session else None
    
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url')
        download_to_device = data.get('download_to_device', False)
        format_type = data.get('format', 'mp3')  # Default to mp3

        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400

        # Validate YouTube URL
        if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Get video info first to extract title
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = sanitize_filename(info.get('title', 'video'))

        # Choose download location based on preference
        if download_to_device:
            # Download to temp folder first
            import tempfile
            temp_dir = tempfile.mkdtemp()
            filepath = os.path.join(temp_dir, video_title)
        else:
            # Download directly to downloads folder
            filepath = os.path.join(DOWNLOAD_FOLDER, video_title)

        # Configure yt-dlp options based on format
        if format_type == 'mp4':
            # Download video (MP4)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': filepath,
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
            }
        else:
            # Download audio only (MP3)
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': filepath,
                'quiet': True,
                'no_warnings': True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Log successful download
        if user_id:
            db.log_download(
                user_id,
                "youtube",
                video_title,
                youtube_url,
                True,
                None,
                request.remote_addr
            )
            db.log_activity(user_id, "youtube_download", f"Downloaded: {video_title}", request.remote_addr, request.headers.get("User-Agent"))

        if download_to_device:
            # Send file to client
            file_extension = '.mp4' if format_type == 'mp4' else '.mp3'
            downloaded_file = f'{filepath}{file_extension}'
            response = send_from_directory(
                temp_dir,
                f'{video_title}{file_extension}',
                as_attachment=True,
                download_name=f'{video_title}{file_extension}'
            )

            # Clean up temp file after sending
            @response.call_on_close
            def cleanup():
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

            return response
        else:
            file_extension = '.mp4' if format_type == 'mp4' else '.mp3'
            return jsonify({
                'success': True,
                'message': f'Successfully downloaded: {video_title}',
                'filename': f'{video_title}{file_extension}'
            })

    except Exception as e:
        # Log failed download
        session_token = request.cookies.get("session_token")
        session = db.get_session(session_token) if session_token else None
        if session:
            db.log_download(session["user_id"], "youtube", "unknown", youtube_url if "youtube_url" in locals() else None, False, str(e), request.remote_addr)
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/downloads/<path:filename>')
def download_file(filename):
    """Serve downloaded files"""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)



@app.route('/login')
def login_page():
    """Serve login page"""
    return render_template('auth.html')


# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    user_id = db.create_user(username, password, email)

    if not user_id:
        return jsonify({'error': 'Username already exists'}), 400

    # Log activity
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    db.log_activity(user_id, 'register', f'New user registered: {username}', ip_address, user_agent)

    return jsonify({'success': True, 'message': 'User registered successfully'})

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user = db.verify_user(username, password)

    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401

    # Create session
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    session_token = db.create_session(user['id'], ip_address, user_agent)

    # Log activity
    db.log_activity(user['id'], 'login', f'User logged in', ip_address, user_agent)

    # Create response with cookie
    response = make_response(jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'is_admin': bool(user['is_admin'])
        }
    }))

    response.set_cookie('session_token', session_token, max_age=7*24*60*60, httponly=True, samesite='Lax')

    return response

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session_token = request.cookies.get('session_token')

    if session_token:
        session = db.get_session(session_token)
        if session:
            db.log_activity(session['user_id'], 'logout', 'User logged out', request.remote_addr, request.headers.get('User-Agent'))
            db.delete_session(session_token)

    response = make_response(jsonify({'success': True}))
    response.set_cookie('session_token', '', expires=0)

    return response

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current logged in user"""
    session_token = request.cookies.get('session_token')

    if not session_token:
        return jsonify({'authenticated': False}), 200

    session = db.get_session(session_token)

    if not session:
        return jsonify({'authenticated': False}), 200

    return jsonify({
        'authenticated': True,
        'user': {
            'id': session['user_id'],
            'username': session['username'],
            'is_admin': bool(session['is_admin'])
        }
    })

@app.route('/admin')
def admin_page():
    """Serve admin dashboard"""
    session_token = request.cookies.get('session_token')
    session = db.get_session(session_token)

    if not session or not session['is_admin']:
        return render_template('auth.html')

    return render_template('admin.html')

# Admin API endpoints
@app.route('/api/admin/stats', methods=['GET'])
@db.require_admin
def get_admin_stats():
    """Get overall system statistics"""
    stats = db.get_stats()
    return jsonify(stats)

@app.route('/api/admin/users', methods=['GET'])
@db.require_admin
def get_admin_users():
    """Get all users"""
    users = db.get_all_users()
    return jsonify({'users': users})

@app.route('/api/admin/activity', methods=['GET'])
@db.require_admin
def get_admin_activity():
    """Get recent activity"""
    limit = request.args.get('limit', 100, type=int)
    activities = db.get_recent_activity(limit)
    return jsonify({'activities': activities})

@app.route('/api/admin/downloads', methods=['GET'])
@db.require_admin
def get_admin_downloads():
    """Get download history"""
    limit = request.args.get('limit', 100, type=int)
    downloads = db.get_download_history(limit)
    return jsonify({'downloads': downloads})
if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
