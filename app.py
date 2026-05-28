import database as db
from flask import Flask, render_template, request, jsonify, send_from_directory
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import hmac
import os
import re
from functools import wraps
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
DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', 'downloads')
ALLOW_SERVER_STORAGE = os.getenv('ALLOW_SERVER_STORAGE', 'false').lower() == 'true'
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

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
        return None
    
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        return spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    except Exception as e:
        app.logger.error(f"Failed to initialize Spotify client: {e}")
        return None

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


def spotify_api_error_response(error):
    """Convert Spotify API failures into user-facing JSON responses."""
    status_code = getattr(error, 'http_status', None) or 502
    raw_message = str(error)
    lower_message = raw_message.lower()

    if status_code == 403 and 'premium subscription' in lower_message:
        message = (
            'Spotify blocked this request because the Spotify developer app owner '
            'does not have an active Premium subscription. Add Premium to the '
            'Spotify account that owns the app, then wait a few hours for Spotify '
            'to allow API requests again.'
        )
    elif status_code == 403:
        message = (
            'Spotify blocked this playlist request. In Development Mode, Spotify '
            'now restricts some playlist data to apps/users that meet its current '
            'access rules.'
        )
    elif status_code == 404:
        message = 'Spotify could not find that playlist. Check that the playlist URL is correct and public.'
    else:
        message = f'Spotify request failed: {raw_message}'

    app.logger.warning('Spotify API error: %s', raw_message)
    return jsonify({'error': message}), status_code

def sanitize_filename(filename):
    """Clean filename for safe file system storage"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    filename = filename[:200]
    return filename.strip()


def get_request_ip():
    """Resolve the client IP, preferring the forwarded address when present."""
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr


def admin_auth_required_response():
    """Return an HTTP Basic auth challenge for the admin area."""
    is_api_request = request.path.startswith('/api/')
    payload = {'error': 'Admin authentication required'} if is_api_request else 'Admin authentication required'
    status = 401
    headers = {'WWW-Authenticate': 'Basic realm="Admin Dashboard"'}
    return payload, status, headers


def is_admin_authorized():
    """Validate the HTTP Basic credentials for the admin area."""
    auth = request.authorization

    if not ADMIN_PASSWORD or not auth:
        return False

    return (
        hmac.compare_digest(auth.username or '', ADMIN_USERNAME)
        and hmac.compare_digest(auth.password or '', ADMIN_PASSWORD)
    )


def require_admin_password(view_func):
    """Protect admin HTML and API routes with one shared password."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_admin_authorized():
            return admin_auth_required_response()
        return view_func(*args, **kwargs)

    return wrapped

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
        data = request.get_json(silent=True) or {}
        playlist_url = data.get('playlist_url')
        
        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400
        
        sp = get_spotify_client()
        if not sp:
            return jsonify({
                'error': 'Spotify API is not configured on this server. Please use the "Import TXT/CSV" feature instead.'
            }), 501

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

        db.log_activity(
            'spotify_playlist_lookup',
            f"Fetched playlist info: {playlist['name']}",
            get_request_ip()
        )
        
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
    except SpotifyException as e:
        return spotify_api_error_response(e)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def search_youtube_video(song_name, artist):
    """Find best matching YouTube video"""
    query = f"{artist} {song_name} official audio".strip()
    return f"ytsearch1:{query}"

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
        data = request.get_json(silent=True) or {}
        tracks_info = data.get('tracks') or []
        playlist_name = sanitize_filename(data.get('playlist_name') or 'imported-playlist')
        resume = data.get('resume', False)
        download_to_device = data.get('download_to_device', False)
        format_type = data.get('format', 'mp3')  # Default to mp3

        if not tracks_info:
            return jsonify({'error': 'Import a TXT or CSV playlist file first.'}), 400

        tracks_info = [
            {
                'name': str(track.get('name', '')).strip(),
                'artist': str(track.get('artist') or 'Unknown').strip()
            }
            for track in tracks_info
            if str(track.get('name', '')).strip()
        ]

        if not tracks_info:
            return jsonify({'error': 'No valid songs were found in the imported file.'}), 400

        # Choose download location
        if download_to_device:
            import tempfile
            playlist_folder = tempfile.mkdtemp()
        else:
            playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_name)
            os.makedirs(playlist_folder, exist_ok=True)

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
                'playlist_url': '',
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
                db.log_download(
                    'playlist',
                    track_name,
                    playlist_name,
                    False,
                    'YouTube video not found',
                    get_request_ip()
                )
                continue

            # Download from YouTube to playlist folder
            success = download_from_youtube(youtube_url, track['artist'], track['name'], playlist_folder, format_type)

            if success:
                download_progress['completed'].append(track_name)
                db.log_download(
                    'playlist',
                    track_name,
                    playlist_name,
                    True,
                    None,
                    get_request_ip()
                )
            else:
                download_progress['failed'].append({
                    'track': track_name,
                    'reason': 'Download failed'
                })
                db.log_download(
                    'playlist',
                    track_name,
                    playlist_name,
                    False,
                    'Download failed',
                    get_request_ip()
                )

            # Small delay to avoid rate limits
            time.sleep(1)

        download_progress['status'] = 'completed'
        db.log_activity(
            'imported_playlist_download',
            f"Processed imported playlist: {playlist_name}",
            get_request_ip()
        )

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

    except SpotifyException as e:
        download_progress['status'] = 'error'
        return spotify_api_error_response(e)

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

        db.log_download(
            "youtube",
            video_title,
            youtube_url,
            True,
            None,
            get_request_ip()
        )
        db.log_activity(
            "youtube_download",
            f"Downloaded: {video_title}",
            get_request_ip()
        )

        if download_to_device:
            # Send file to client
            file_extension = '.mp4' if format_type == 'mp4' else '.mp3'
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
        db.log_download(
            "youtube",
            "unknown",
            youtube_url if "youtube_url" in locals() else None,
            False,
            str(e),
            get_request_ip()
        )
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/downloads/<path:filename>')
def download_file(filename):
    """Serve downloaded files"""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

@app.route('/api/youtube/playlist/info', methods=['POST'])
def get_youtube_playlist_info():
    """Get YouTube playlist metadata"""
    try:
        data = request.get_json()
        playlist_url = data.get('playlist_url')

        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400

        # Validate YouTube playlist URL
        if 'youtube.com/playlist' not in playlist_url and 'youtu.be' not in playlist_url:
            return jsonify({'error': 'Invalid YouTube playlist URL'}), 400

        # Extract playlist info using yt-dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just extract info
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)

            if not playlist_info:
                return jsonify({'error': 'Failed to fetch playlist information'}), 500

            videos = []
            for entry in playlist_info.get('entries', []):
                if entry:
                    videos.append({
                        'title': entry.get('title', 'Unknown'),
                        'channel': entry.get('uploader', 'Unknown'),
                        'url': entry.get('url', '')
                    })

            db.log_activity(
                'youtube_playlist_lookup',
                f"Fetched playlist info: {playlist_info.get('title', 'Unknown Playlist')}",
                get_request_ip()
            )

            return jsonify({
                'success': True,
                'playlist': {
                    'name': playlist_info.get('title', 'Unknown Playlist'),
                    'description': playlist_info.get('description', ''),
                    'video_count': len(videos),
                    'thumbnail': playlist_info.get('thumbnail', ''),
                    'videos': videos
                }
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/youtube/playlist/download', methods=['POST'])
def download_youtube_playlist():
    """Download entire YouTube playlist"""
    global download_progress

    try:
        data = request.get_json()
        playlist_url = data.get('playlist_url')
        resume = data.get('resume', False)
        download_to_device = data.get('download_to_device', False)
        format_type = data.get('format', 'mp3')

        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400

        # Validate YouTube playlist URL
        if 'youtube.com/playlist' not in playlist_url and 'youtu.be' not in playlist_url:
            return jsonify({'error': 'Invalid YouTube playlist URL'}), 400

        # Extract playlist info
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            playlist_name = sanitize_filename(playlist_info.get('title', 'youtube_playlist'))
            entries = playlist_info.get('entries', [])

        # Choose download location
        if download_to_device:
            import tempfile
            playlist_folder = tempfile.mkdtemp()
        else:
            playlist_folder = os.path.join(DOWNLOAD_FOLDER, playlist_name)
            os.makedirs(playlist_folder, exist_ok=True)

        # Prepare video list
        videos_info = []
        for entry in entries:
            if entry:
                videos_info.append({
                    'title': entry.get('title', 'Unknown'),
                    'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                })

        # If not resuming, reset progress
        if not resume:
            download_progress = {
                'current': 0,
                'total': len(videos_info),
                'current_track': '',
                'status': 'downloading',
                'completed': [],
                'failed': [],
                'should_stop': False,
                'playlist_name': playlist_name,
                'playlist_url': playlist_url,
                'tracks_info': videos_info
            }
        else:
            download_progress['should_stop'] = False
            download_progress['status'] = 'downloading'

        # Download each video
        start_index = download_progress['current'] if resume else 0

        for idx in range(start_index, len(videos_info)):
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

            video = videos_info[idx]
            download_progress['current'] = idx + 1
            download_progress['current_track'] = video['title']

            # Check if already downloaded
            if video['title'] in download_progress['completed']:
                continue

            try:
                # Download video
                filename = sanitize_filename(video['title'])
                filepath = os.path.join(playlist_folder, filename)

                # Configure yt-dlp options based on format
                if format_type == 'mp4':
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'outtmpl': filepath,
                        'quiet': True,
                        'no_warnings': True,
                        'merge_output_format': 'mp4',
                    }
                else:
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
                    ydl.download([video['url']])

                download_progress['completed'].append(video['title'])
                db.log_download(
                    'youtube_playlist',
                    video['title'],
                    playlist_url,
                    True,
                    None,
                    get_request_ip()
                )

            except Exception as e:
                download_progress['failed'].append({
                    'track': video['title'],
                    'reason': str(e)
                })
                db.log_download(
                    'youtube_playlist',
                    video['title'],
                    playlist_url,
                    False,
                    str(e),
                    get_request_ip()
                )

            # Small delay to avoid rate limits
            time.sleep(1)

        download_progress['status'] = 'completed'
        db.log_activity(
            "youtube_playlist_download",
            f"Processed playlist: {playlist_name}",
            get_request_ip()
        )

        if download_to_device:
            # Create ZIP file and send to client
            import zipfile
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
                'message': f"Downloaded {len(download_progress['completed'])} of {download_progress['total']} videos",
                'completed': len(download_progress['completed']),
                'failed': len(download_progress['failed'])
            })

    except Exception as e:
        download_progress['status'] = 'error'
        return jsonify({'error': str(e)}), 500

@app.route('/admin')
@require_admin_password
def admin_page():
    """Serve admin dashboard"""
    return render_template('admin.html')

# Admin API endpoints
@app.route('/api/admin/stats', methods=['GET'])
@require_admin_password
def get_admin_stats():
    """Get overall system statistics"""
    stats = db.get_stats()
    return jsonify(stats)

@app.route('/api/admin/activity', methods=['GET'])
@require_admin_password
def get_admin_activity():
    """Get recent activity"""
    limit = request.args.get('limit', 100, type=int)
    activities = db.get_recent_activity(limit)
    return jsonify({'activities': activities})

@app.route('/api/admin/downloads', methods=['GET'])
@require_admin_password
def get_admin_downloads():
    """Get download history"""
    limit = request.args.get('limit', 100, type=int)
    downloads = db.get_download_history(limit)
    return jsonify({'downloads': downloads})
if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
