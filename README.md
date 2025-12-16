# 🎵 Spotify Playlist Downloader

A powerful web application to download songs from your Spotify playlists locally. The app fetches playlist data from Spotify, searches for matching YouTube videos, and downloads them as MP3 files using yt-dlp.

## ⚠️ Legal Disclaimer

**This tool is for personal use only.** You are responsible for respecting copyright laws and the Terms of Service of Spotify and YouTube. Only download content you have the rights to download.

## ✨ Features

- 🎼 Fetch any public Spotify playlist
- 🔍 Automatic YouTube search for each track
- 📥 Download as high-quality MP3 files (192kbps)
- 📁 **Auto-organize: Each playlist gets its own folder**
- ⏸️ **Stop/Resume: Pause and resume downloads anytime**
- 🎬 **Direct YouTube Download: Download any YouTube video as MP3**
- 🎵 **Smart Deduplication: Combine all songs into one folder without duplicates**
- 📊 Real-time progress tracking
- 🎨 Clean, responsive web interface
- 💾 Runs completely locally
- 🌐 **Access from any device on your network**
- 📝 Track list preview before downloading
- ✅ Success/failure tracking for each download
- 🆓 **No API keys needed - completely free!**

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio conversion)
- Spotify Developer account (free)

### 1. Clone the Repository

```bash
git clone https://github.com/sohaibmokhliss/spotifyPLdownloader.git
cd spotifyPLdownloader
```

### 2. Install System Dependencies

**On Arch Linux:**
```bash
sudo pacman -S ffmpeg python-pip
```

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg python3-pip
```

**On macOS:**
```bash
brew install ffmpeg
```

**On Windows:**
Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

### 3. Set Up Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Get Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create App"
3. Fill in app name and description
4. Copy your **Client ID** and **Client Secret**

### 6. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Spotify credentials:

```env
SPOTIFY_CLIENT_ID=your_actual_client_id
SPOTIFY_CLIENT_SECRET=your_actual_client_secret
DOWNLOAD_FOLDER=downloads
FLASK_PORT=5000
```

### 7. Run the Application

```bash
python app.py
# Or with virtual environment:
./venv/bin/python app.py
```

The app will be accessible at:
- **Local machine**: http://localhost:5000
- **Other devices on network**: http://YOUR_LOCAL_IP:5000

## 📖 How to Use

### 1. Download Spotify Playlists

#### Get Spotify Playlist URL
- Open Spotify (desktop or mobile)
- Go to any playlist
- Click Share → Copy link to playlist
- Example: `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`

#### Fetch and Download
- Open the app in your browser
- Paste the playlist URL
- Click "Fetch Playlist"
- Review the tracks
- Click "📥 Download All" to start
- **Use "⏸️ Stop Download"** to pause after the current track
- **Use "▶️ Resume Download"** to continue from where you left off
- Watch real-time progress
- Find downloaded files in `downloads/PLAYLIST_NAME/` folder

### 2. Download YouTube Videos Directly

- Scroll to the "Direct YouTube Download" section
- Paste any YouTube video URL
- Click "Download MP3"
- Files are saved directly to `downloads/` folder (not in a playlist subfolder)
- Example: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`

### 3. Create Deduplicated All Songs Folder

- After downloading multiple playlists, scroll to the "ORGANIZE" section
- Click "🎵 Create All Songs Folder"
- The app will:
  - Scan all MP3 files in your downloads folder
  - Identify and remove duplicates
  - Copy unique songs to `downloads/all_songs/` folder
- View statistics showing files scanned, unique tracks, and duplicates found

### 4. Access from Other Devices

The app is accessible from any device on your network:

1. Find your computer's local IP:
   ```bash
   # Linux/Mac
   ip addr show | grep "inet " | grep -v "127.0.0.1"

   # Windows
   ipconfig
   ```

2. On your phone/tablet, open browser and go to:
   ```
   http://YOUR_LOCAL_IP:5000
   ```

3. Use the app just like on your computer!

## 📁 Project Structure

```
spotifyPLdownloader/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── .env                  # Your credentials (git-ignored)
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── venv/                # Virtual environment (created after setup)
├── templates/
│   └── index.html       # Web interface
├── static/
│   ├── style.css        # Styling
│   └── script.js        # Frontend logic
└── downloads/           # Downloaded MP3s (git-ignored)
    ├── Playlist 1/      # Each playlist gets its own folder
    ├── Playlist 2/
    └── ...
```

## 🛠️ How It Works

1. **Spotify Integration**: Fetches playlist metadata using Spotify Web API
2. **YouTube Search**: Searches for matching videos using youtube-search-python
3. **MP3 Download**: Downloads and converts to MP3 using yt-dlp (no API keys required!)
4. **Smart Organization**: Creates separate folders for each playlist automatically
5. **Direct YouTube Downloads**: Extract and download any YouTube video directly to MP3
6. **Deduplication**: Scans all downloads recursively and identifies duplicates by filename
7. **Progress Tracking**: Real-time updates via polling endpoint
8. **Resume Support**: Tracks completed downloads to skip them when resuming
9. **File Management**: Saves MP3 files with sanitized filenames

## 🔧 Troubleshooting

### "Spotify credentials not configured"
- Make sure you've created a `.env` file
- Check that your Client ID and Secret are correct
- Restart the Flask app after changing `.env`

### "YouTube video not found"
- Some tracks might not be available on YouTube
- The app will skip unavailable tracks automatically
- Check the "Failed" list to see which tracks couldn't be downloaded

### "Download failed"
- Make sure FFmpeg is installed: `ffmpeg -version`
- Check your internet connection
- Some videos may be age-restricted or region-locked

### Downloads are slow
- This is normal - each track is searched and downloaded individually
- Downloading and converting high-quality audio takes time
- The app adds 1-second delays to avoid rate limiting
- Expect 5-15 seconds per track depending on your connection

### Can't access from other devices
- Make sure both devices are on the same WiFi/network
- Check if your firewall is blocking port 5000
- Verify you're using the correct local IP address

### "ModuleNotFoundError" when running
- Make sure you're using the virtual environment:
  ```bash
  source venv/bin/activate  # or ./venv/bin/python app.py
  ```
- Reinstall dependencies: `pip install -r requirements.txt`

## ⚙️ Configuration

Edit `.env` to customize:

```env
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here

# App Configuration
DOWNLOAD_FOLDER=downloads    # Change download location
FLASK_PORT=5000              # Change port number
FLASK_ENV=development        # Set to 'production' for deployment
```

## 🚀 Deployment Guide

### **For Public Hosting (Recommended Settings)**

The app is configured by default to be safe for public access. All downloads go directly to users' devices, protecting your server storage.

#### **Quick Deploy Steps:**

1. **Set Environment Variables:**
```bash
# Required
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret

# Recommended for public hosting
ALLOW_SERVER_STORAGE=false  # Default - keeps your server storage safe
FLASK_ENV=production
FLASK_PORT=5000
```

2. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run with Production Server:**
```bash
# Using Gunicorn (recommended)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or using Flask (development only)
python app.py
```

4. **Optional: Set up as a Service** (systemd example)
```bash
sudo nano /etc/systemd/system/spotify-downloader.service
```

```ini
[Unit]
Description=Spotify Playlist Downloader
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/spotifyPLdownloader
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable spotify-downloader
sudo systemctl start spotify-downloader
```

5. **Set up Reverse Proxy** (nginx example)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

6. **Enable HTTPS** (using certbot)
```bash
sudo certbot --nginx -d your-domain.com
```

### **Security Considerations for Public Hosting:**

✅ **Default Configuration is Safe:**
- `ALLOW_SERVER_STORAGE=false` prevents users from filling your disk
- All downloads go to users' devices automatically
- No authentication required for basic usage

⚠️ **Additional Security Measures:**
- Use a reverse proxy (nginx/Apache) with rate limiting
- Enable HTTPS for encrypted connections
- Consider adding authentication for private deployments
- Monitor server resources and set up alerts
- Keep dependencies updated: `pip install -U -r requirements.txt`

### **For Private/Personal Use:**

If you want to save files to the server for personal use:

```bash
# In your .env file
ALLOW_SERVER_STORAGE=true
```

This will show the download location toggle, allowing you to choose between server and device downloads.

## 🎯 Features Explained

### Playlist-Specific Folders
Each Spotify playlist is downloaded into its own folder named after the playlist:
```
downloads/
├── Chill Vibes/
│   ├── Artist - Song 1.mp3
│   └── Artist - Song 2.mp3
├── Workout Mix/
│   ├── Artist - Song 3.mp3
│   └── Artist - Song 4.mp3
├── video_title.mp3         # Direct YouTube downloads
└── all_songs/              # Deduplicated collection
    ├── Artist - Song 1.mp3
    ├── Artist - Song 3.mp3
    └── Artist - Song 4.mp3
```

### Stop/Resume Functionality
- **Stop**: Safely pause downloads after the current track finishes
- **Resume**: Continue from exactly where you left off
- Already downloaded tracks are automatically skipped
- Perfect for large playlists or unstable connections

### Direct YouTube Download
- Download any YouTube video directly as MP3
- No need to create a playlist first
- Files go directly to `downloads/` folder
- Perfect for single songs or videos

### Smart Deduplication
- Scans all playlists and finds duplicate songs
- Creates `all_songs/` folder with unique tracks only
- Shows detailed statistics (files scanned, duplicates found, etc.)
- Non-destructive - original playlist folders remain untouched
- Perfect for creating a master library from multiple playlists

## 🤝 Contributing

Feel free to open issues or submit pull requests!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is for educational purposes only. Use responsibly and respect copyright laws.

## 🙏 Credits

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/)
- [YouTube Search Python](https://github.com/alexmercerind/youtube-search-python)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The best YouTube downloader
- [Flask](https://flask.palletsprojects.com/)
- [FFmpeg](https://ffmpeg.org/) - Audio/video processing

## 🎓 FAQ

**Q: Do I need to pay for any API services?**
A: No! The app uses yt-dlp which is completely free. You only need free Spotify API credentials.

**Q: Can I download private playlists?**
A: No, only public Spotify playlists are supported. However, you can download any public YouTube video directly.

**Q: What quality are the downloads?**
A: MP3 files at 192kbps, which provides excellent quality for most use cases.

**Q: Can multiple people use the app at once?**
A: The app handles one download session at a time. Multiple users can access it, but downloads will queue.

**Q: Where are my downloaded files?**
A: In the `downloads/` folder. Spotify playlists get their own subfolders, YouTube direct downloads go to the root downloads folder, and deduplicated songs go to `downloads/all_songs/`.

**Q: What happens to my original playlists when I create the all_songs folder?**
A: Nothing! The deduplication feature copies files, it doesn't move them. Your original playlist folders remain untouched.

**Q: How does the app detect duplicates?**
A: Songs are compared by filename (e.g., "Artist - Track.mp3"). If two songs have the same filename, they're considered duplicates and only one copy is kept in the all_songs folder.

**Q: Can I download YouTube playlists?**
A: Not currently. You can download individual YouTube videos, or use Spotify playlists which automatically search YouTube for each track.

**Q: Can I run this on a server?**
A: Yes! Set `FLASK_ENV=production` and use a production WSGI server like Gunicorn. See the Deployment Guide section.

**Q: Is it safe to host this publicly?**
A: Yes! By default, `ALLOW_SERVER_STORAGE=false` means all downloads go to users' devices, not your server. Your disk space is protected.

**Q: How do I prevent people from filling up my server storage?**
A: The default configuration (`ALLOW_SERVER_STORAGE=false`) already does this. Users can only download files to their own devices.

**Q: Can I host this for free?**
A: Yes, you can deploy on platforms like Railway, Render, or Heroku. Just make sure FFmpeg is available in the environment.

---

**Made with ❤️ for personal use** 🎧 Enjoy your music locally!
