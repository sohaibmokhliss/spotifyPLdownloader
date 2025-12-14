let progressInterval = null;

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

async function fetchPlaylist() {
    const playlistUrl = document.getElementById('playlistUrl').value.trim();
    
    if (!playlistUrl) {
        showError('Please enter a playlist URL');
        return;
    }
    
    const fetchBtn = document.getElementById('fetchBtn');
    fetchBtn.disabled = true;
    fetchBtn.textContent = 'Fetching...';
    
    try {
        const response = await fetch('/api/playlist/info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ playlist_url: playlistUrl })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch playlist');
        }
        
        displayPlaylistInfo(data.playlist);
        
    } catch (error) {
        showError(error.message);
    } finally {
        fetchBtn.disabled = false;
        fetchBtn.textContent = 'Fetch Playlist';
    }
}

function displayPlaylistInfo(playlist) {
    const infoDiv = document.getElementById('playlistInfo');
    
    document.getElementById('playlistName').textContent = playlist.name;
    document.getElementById('playlistDescription').textContent = playlist.description || 'No description';
    document.getElementById('trackCount').textContent = `${playlist.track_count} tracks`;
    
    if (playlist.image) {
        document.getElementById('playlistImage').src = playlist.image;
    }
    
    const trackListDiv = document.getElementById('trackList');
    trackListDiv.innerHTML = '';
    
    playlist.tracks.forEach((track, index) => {
        const trackDiv = document.createElement('div');
        trackDiv.className = 'track-item';
        trackDiv.innerHTML = `
            <div class="track-info">
                <div class="track-name">${index + 1}. ${track.name}</div>
                <div class="track-artist">${track.artist}</div>
            </div>
        `;
        trackListDiv.appendChild(trackDiv);
    });
    
    infoDiv.style.display = 'block';
    
    infoDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function downloadPlaylist() {
    const playlistUrl = document.getElementById('playlistUrl').value.trim();
    
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Downloading...';
    
    const progressSection = document.getElementById('progressSection');
    progressSection.style.display = 'block';
    
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('completedList').innerHTML = '';
    document.getElementById('failedList').innerHTML = '';
    document.getElementById('completedCount').textContent = '0';
    document.getElementById('failedCount').textContent = '0';
    
    startProgressPolling();
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ playlist_url: playlistUrl })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Download failed');
        }
        
        updateProgress();
        
        alert(`Download complete! ${data.completed} tracks downloaded successfully.`);
        
    } catch (error) {
        showError(error.message);
    } finally {
        stopProgressPolling();
        downloadBtn.disabled = false;
        downloadBtn.textContent = '📥 Download All';
    }
}

function startProgressPolling() {
    progressInterval = setInterval(updateProgress, 1000);
}

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

async function updateProgress() {
    try {
        const response = await fetch('/api/progress');
        const progress = await response.json();
        
        const percentage = progress.total > 0 
            ? Math.round((progress.current / progress.total) * 100) 
            : 0;
        
        document.getElementById('progressBar').style.width = percentage + '%';
        document.getElementById('progressText').textContent = 
            `${progress.current} of ${progress.total} tracks processed (${percentage}%)`;
        document.getElementById('currentTrack').textContent = 
            progress.current_track ? `Currently downloading: ${progress.current_track}` : '';
        
        const completedList = document.getElementById('completedList');
        completedList.innerHTML = '';
        progress.completed.forEach(track => {
            const li = document.createElement('li');
            li.textContent = track;
            completedList.appendChild(li);
        });
        document.getElementById('completedCount').textContent = progress.completed.length;
        
        const failedList = document.getElementById('failedList');
        failedList.innerHTML = '';
        progress.failed.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.track} (${item.reason})`;
            failedList.appendChild(li);
        });
        document.getElementById('failedCount').textContent = progress.failed.length;
        
        if (progress.status === 'completed' || progress.status === 'error') {
            stopProgressPolling();
        }
        
    } catch (error) {
        console.error('Failed to update progress:', error);
    }
}

document.getElementById('playlistUrl').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        fetchPlaylist();
    }
});