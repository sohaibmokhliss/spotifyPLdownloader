# 🎵 Spotify Playlist Downloader

A simple web application to download songs from your Spotify playlists locally. The app fetches playlist data from Spotify, searches for matching YouTube videos, and downloads them as MP3 files using RapidAPI.

## ⚠️ Legal Disclaimer

**This tool is for personal use only.** You are responsible for respecting copyright laws and the Terms of Service of Spotify and YouTube. Only download content you have the rights to download.

## ✨ Features

- 🎼 Fetch any public Spotify playlist
- 🔍 Automatic YouTube search for each track
- 📥 Download as MP3 files
- 📊 Real-time progress tracking
- 🎨 Clean, simple web interface
- 💾 Runs completely locally
- 📝 Track list preview before downloading
- ✅ Success/failure tracking for each download

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Spotify Developer account
- RapidAPI account

### 1. Clone the Repository

```bash
git clone https://github.com/sohaibmokhliss/spotifyPLdownloader.git
cd spotifyPLdownloader
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Get API Credentials

#### Spotify API:
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create App"
3. Fill in app name and description
4. Copy your **Client ID** and **Client Secret**

#### RapidAPI (YouTube-to-MP3):
1. Go to [RapidAPI YouTube-to-MP3](https://rapidapi.com/marcoCollatina/api/youtube-to-mp315)
2. Subscribe to the API (free tier available)
3. Copy your **API Key**

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
SPOTIFY_CLIENT_ID=your_actual_client_id
SPOTIFY_CLIENT_SECRET=your_actual_client_secret
RAPIDAPI_KEY=your_rapidapi_key
```

### 5. Run the Application

```bash
python app.py
```

Open your browser and go to: **http://localhost:5000**

## 📖 How to Use

1. **Get Spotify Playlist URL:**
   - Open Spotify
   - Go to any playlist
   - Click Share → Copy link to playlist
   - Example: `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`

2. **Paste URL in the app:**
   - Paste the playlist URL
   - Click "Fetch Playlist"
   - Review the tracks

3. **Download:**
   - Click "Download All"
   - Watch progress in real-time
   - Find downloaded files in the `downloads/` folder

## 📁 Project Structure

```
spotifyPLdownloader/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── .env                  # Your credentials (git-ignored)
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── templates/
│   └── index.html       # Web interface
├── static/
│   ├── style.css        # Styling
│   └── script.js        # Frontend logic
└── downloads/           # Downloaded MP3s (git-ignored)
```

## 🛠️ How It Works

1. **Spotify Integration**: Fetches playlist metadata using Spotify Web API
2. **YouTube Search**: Searches for matching videos using youtube-search-python
3. **MP3 Conversion**: Downloads and converts videos using RapidAPI YouTube-to-MP3 service
4. **Progress Tracking**: Real-time updates via polling endpoint
5. **File Management**: Saves MP3 files with sanitized filenames

## 🔧 Troubleshooting

### "Spotify credentials not configured"
- Make sure you've created a `.env` file
- Check that your Client ID and Secret are correct
- Restart the Flask app after changing `.env`

### "YouTube video not found"
- Some tracks might not be available on YouTube
- Try searching manually to verify
- The app will skip unavailable tracks

### "Download failed"
- Check your RapidAPI subscription is active
- Verify API key is correct
- Check rate limits on your RapidAPI plan

### Downloads are slow
- This is normal - each track needs to be searched and downloaded
- The app adds small delays to respect rate limits
- Expect 5-10 seconds per track

## ⚙️ Configuration

Edit `.env` to customize:

```env
DOWNLOAD_FOLDER=my_music     # Change download location
FLASK_PORT=8080              # Change port number
FLASK_ENV=production         # Production mode
```

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
- [RapidAPI YouTube-to-MP3](https://rapidapi.com/marcoCollatina/api/youtube-to-mp315)
- [Flask](https://flask.palletsprojects.com/)

---

**Made with ❤️ for personal use** 🎧 Enjoy your music locally!