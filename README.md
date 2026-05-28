# Spotify Playlist Downloader (Educational Project)

A Flask-based web application that allows you to import Spotify playlists (via TXT/CSV export) and download the corresponding tracks from YouTube as MP3 or MP4.

## ⚠️ Legal Disclaimer

**This project is for educational purposes only.** 

- This tool is designed to demonstrate how to integrate various APIs (Spotify, YouTube search) and media processing libraries (`yt-dlp`).
- The author does not condone or encourage the unauthorized downloading of copyrighted material.
- Users are solely responsible for their own actions and must comply with the Terms of Service of both Spotify and YouTube.
- **Do not host this application publicly.** It is intended for local, personal, and educational use.

## Features

- **Import via TXT/CSV:** No Spotify API keys required for this flow. Export your playlist from [Chosic](https://www.chosic.com/spotify-playlist-exporter/) and drop the file in.
- **YouTube Video/Playlist Download:** Paste any YouTube URL to download single videos or entire playlists.
- **Format Options:** Download as MP3 (Audio) or MP4 (Video).
- **Download to Device:** Files are zipped and sent directly to your browser (no server storage needed).
- **Admin Dashboard:** Monitor local activity and download history.

## How It Works (Preferred Flow)

1.  **Export:** Go to [Chosic Spotify Playlist Exporter](https://www.chosic.com/spotify-playlist-exporter/).
2.  **Export as Text/CSV:** Download your playlist file.
3.  **Upload:** Open this app locally and drag-and-drop the file.
4.  **Download:** Click "Download All". The app will search YouTube for each track and download the best match.

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/your-username/spotifyPLdownloader.git
cd spotifyPLdownloader
```

### 2. Install dependencies
It is recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```
*Note: Spotify API keys are optional if you only use the TXT/CSV import feature.*

### 4. Run the application
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

## Tech Stack

- **Backend:** Flask (Python)
- **Media Engine:** `yt-dlp`
- **Search:** `youtube-search-python`
- **Database:** SQLite (for local logging)
- **Frontend:** Vanilla JS/CSS

## License

This project is open-sourced under the MIT License. See the [LICENSE](LICENSE) file for more details.
