from flask import Flask, render_template, request, jsonify, send_from_directory
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

# Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'youtube-to-mp315.p.rapidapi.com')
DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', 'downloads')

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

def download_mp3_from_youtube(youtube_url, artist, track_name, download_folder=DOWNLOAD_FOLDER):
    """Download MP3 using yt-dlp"""
    try:
        filename = sanitize_filename(f"{artist} - {track_name}")
        filepath = os.path.join(download_folder, filename)

        # yt-dlp options
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

        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400

        sp = get_spotify_client()
        playlist_id = extract_playlist_id(playlist_url)

        # Get playlist details
        playlist = sp.playlist(playlist_id)
        playlist_name = sanitize_filename(playlist['name'])

        # Create playlist-specific folder
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

            # Download MP3 to playlist folder
            success = download_mp3_from_youtube(youtube_url, track['artist'], track['name'], playlist_folder)

            if success:
                download_progress['completed'].append(track_name)
            else:
                download_progress['failed'].append({
                    'track': track_name,
                    'reason': 'Download failed'
                })

            # Small delay to avoid rate limits
            time.sleep(1)

        download_progress['status'] = 'completed'

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

@app.route('/downloads/<path:filename>')
def download_file(filename):
    """Serve downloaded files"""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)