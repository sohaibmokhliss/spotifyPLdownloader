let progressInterval = null;
let downloadLocation = "device";
let allowServerStorage = false;
let importedPlaylist = null;

function showMessage(message, tone = "info") {
    const notice = document.getElementById("globalMessage");
    if (!notice) {
        return;
    }

    clearTimeout(showMessage.timeoutId);
    notice.textContent = message;
    notice.className = `notice notice-${tone}`;
    notice.hidden = false;

    const timeout = tone === "error" ? 12000 : 5000;

    showMessage.timeoutId = setTimeout(() => {
        notice.hidden = true;
    }, timeout);
}

function showError(message) {
    showMessage(message, "error");
}

function showSuccess(message) {
    showMessage(message, "success");
}

function setInlineStatus(elementId, message, tone = "info") {
    const status = document.getElementById(elementId);
    if (!status) {
        return;
    }

    status.textContent = message;
    status.className = `inline-status inline-status-${tone}`;
    status.hidden = false;
}

function clearInlineStatus(elementId) {
    const status = document.getElementById(elementId);
    if (!status) {
        return;
    }

    status.hidden = true;
    status.textContent = "";
    status.className = "inline-status";
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(anchor);
}

async function parseBlobError(blob) {
    const text = await blob.text();

    try {
        const data = JSON.parse(text);
        return data.error || "Download failed";
    } catch {
        return text || "Download failed";
    }
}

function createTrackRow(index, title, meta) {
    const row = document.createElement("div");
    row.className = "track-item";

    const indexBadge = document.createElement("div");
    indexBadge.className = "track-index";
    indexBadge.textContent = index + 1;

    const body = document.createElement("div");

    const titleElement = document.createElement("div");
    titleElement.className = "track-name";
    titleElement.textContent = title;

    const metaElement = document.createElement("div");
    metaElement.className = "track-meta";
    metaElement.textContent = meta;

    body.appendChild(titleElement);
    body.appendChild(metaElement);
    row.appendChild(indexBadge);
    row.appendChild(body);

    return row;
}

function togglePlaybackButtons(mode, activeState) {
    const states = {
        spotify: ["downloadBtn", "stopBtn", "resumeBtn"],
        youtubePlaylist: ["downloadYoutubePlaylistBtn", "stopYoutubePlaylistBtn", "resumeYoutubePlaylistBtn"],
    };

    Object.entries(states).forEach(([key, ids]) => {
        const [downloadId, stopId, resumeId] = ids;
        const isTarget = key === mode;

        document.getElementById(downloadId).disabled = isTarget && activeState === "downloading";
        document.getElementById(stopId).hidden = !(isTarget && activeState === "downloading");
        document.getElementById(resumeId).hidden = !(isTarget && activeState === "paused");
    });
}

function resetProgressPanel() {
    document.getElementById("progressBar").style.width = "0%";
    document.getElementById("progressBar").textContent = "";
    document.getElementById("progressText").textContent = "Waiting for the download to start.";
    document.getElementById("currentTrack").textContent = "";
    document.getElementById("completedList").innerHTML = "";
    document.getElementById("failedList").innerHTML = "";
    document.getElementById("completedCount").textContent = "0";
    document.getElementById("failedCount").textContent = "0";
}

function renderProgress(progress) {
    const percentage = progress.total > 0
        ? Math.round((progress.current / progress.total) * 100)
        : 0;

    const progressBar = document.getElementById("progressBar");
    progressBar.style.width = `${percentage}%`;
    progressBar.textContent = percentage >= 14 ? `${percentage}%` : "";

    document.getElementById("progressText").textContent =
        progress.total > 0
            ? `${progress.current} of ${progress.total} items processed`
            : "Waiting for the next request.";

    document.getElementById("currentTrack").textContent = progress.current_track
        ? `Current item: ${progress.current_track}`
        : "";

    const completedList = document.getElementById("completedList");
    completedList.innerHTML = "";
    progress.completed.forEach((track) => {
        const item = document.createElement("li");
        item.textContent = track;
        completedList.appendChild(item);
    });

    const failedList = document.getElementById("failedList");
    failedList.innerHTML = "";
    progress.failed.forEach((item) => {
        const failedItem = document.createElement("li");
        failedItem.textContent = `${item.track} (${item.reason})`;
        failedList.appendChild(failedItem);
    });

    document.getElementById("completedCount").textContent = String(progress.completed.length);
    document.getElementById("failedCount").textContent = String(progress.failed.length);
}

function splitCsvLine(line) {
    const values = [];
    let current = "";
    let quoted = false;

    for (let index = 0; index < line.length; index += 1) {
        const char = line[index];
        const next = line[index + 1];

        if (char === '"' && quoted && next === '"') {
            current += '"';
            index += 1;
        } else if (char === '"') {
            quoted = !quoted;
        } else if (char === "," && !quoted) {
            values.push(current.trim());
            current = "";
        } else {
            current += char;
        }
    }

    values.push(current.trim());
    return values;
}

function stripTrackPrefix(line) {
    return line
        .replace(/^\s*\d+\s*[\).,-]\s*/, "")
        .replace(/^["']|["']$/g, "")
        .trim();
}

function lineToTrack(line) {
    const cleaned = stripTrackPrefix(line);
    if (!cleaned) {
        return null;
    }

    const dashMatch = cleaned.match(/^(.+?)\s+-\s+(.+)$/);
    if (dashMatch) {
        return {
            artist: dashMatch[1].trim(),
            name: dashMatch[2].trim(),
            album: "",
        };
    }

    const columns = splitCsvLine(cleaned);
    if (columns.length >= 2 && columns[0] && columns[1]) {
        return {
            artist: stripTrackPrefix(columns[0]),
            name: stripTrackPrefix(columns[1]),
            album: columns[2] ? stripTrackPrefix(columns[2]) : "",
        };
    }

    return {
        artist: "Unknown",
        name: cleaned,
        album: "",
    };
}

function parseImportedPlaylist(text, filename) {
    const lines = text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);

    if (!lines.length) {
        throw new Error("The selected file is empty.");
    }

    let tracks = [];
    const firstColumns = splitCsvLine(lines[0]).map((column) => column.toLowerCase());
    const hasHeader = firstColumns.some((column) => /track|title|song|artist/.test(column));

    if (hasHeader) {
        const artistIndex = firstColumns.findIndex((column) => column.includes("artist"));
        const titleIndex = firstColumns.findIndex((column) => /track|title|song|name/.test(column));
        const albumIndex = firstColumns.findIndex((column) => column.includes("album"));

        tracks = lines.slice(1).map((line) => {
            const columns = splitCsvLine(line);
            const artist = artistIndex >= 0 ? columns[artistIndex] : "";
            const name = titleIndex >= 0 ? columns[titleIndex] : "";

            if (!name && !artist) {
                return lineToTrack(line);
            }

            return {
                artist: stripTrackPrefix(artist || "Unknown"),
                name: stripTrackPrefix(name || artist),
                album: albumIndex >= 0 ? stripTrackPrefix(columns[albumIndex] || "") : "",
            };
        });
    } else {
        tracks = lines.map(lineToTrack);
    }

    tracks = tracks.filter((track) => track && track.name);

    if (!tracks.length) {
        throw new Error("No songs could be read from that file.");
    }

    return {
        name: filename.replace(/\.[^.]+$/, "") || "Imported playlist",
        description: "Imported from a TXT or CSV export.",
        track_count: tracks.length,
        image: null,
        tracks,
    };
}

async function handlePlaylistFile(file) {
    if (!file) {
        return;
    }

    try {
        const text = await file.text();
        importedPlaylist = parseImportedPlaylist(text, file.name);
        displayPlaylistInfo(importedPlaylist);
        showSuccess(`Imported ${importedPlaylist.track_count} tracks from ${file.name}.`);
    } catch (error) {
        importedPlaylist = null;
        showError(error.message);
    }
}

function displayPlaylistInfo(playlist) {
    const info = document.getElementById("playlistInfo");
    const image = document.getElementById("playlistImage");

    document.getElementById("playlistName").textContent = playlist.name;
    document.getElementById("playlistDescription").textContent = playlist.description || "No description provided.";
    document.getElementById("trackCount").textContent = `${playlist.track_count} tracks`;

    if (playlist.image) {
        image.src = playlist.image;
        image.hidden = false;
    } else {
        image.hidden = true;
        image.removeAttribute("src");
    }

    const trackList = document.getElementById("trackList");
    trackList.innerHTML = "";

    playlist.tracks.forEach((track, index) => {
        const meta = track.album ? `${track.artist} • ${track.album}` : track.artist;
        trackList.appendChild(createTrackRow(index, track.name, meta));
    });

    info.hidden = false;
    info.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function downloadPlaylist(resume = false) {
    if (!importedPlaylist || !importedPlaylist.tracks.length) {
        showError("Please import a TXT or CSV playlist file first.");
        return;
    }

    const progressSection = document.getElementById("progressSection");
    progressSection.hidden = false;
    if (!resume) {
        resetProgressPanel();
    }

    togglePlaybackButtons("spotify", "downloading");
    startProgressPolling();

    try {
        const response = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                playlist_name: importedPlaylist.name,
                tracks: importedPlaylist.tracks,
                resume,
                download_to_device: downloadLocation === "device",
                format: document.querySelector('input[name="playlistFormat"]:checked').value,
            }),
        });

        if (downloadLocation === "device") {
            const blob = await response.blob();
            if (!response.ok) {
                throw new Error(await parseBlobError(blob));
            }

            downloadBlob(blob, `${importedPlaylist.name || "playlist"}.zip`);
            await updateProgress();
            showSuccess("Playlist archive downloaded to your device.");
            togglePlaybackButtons("spotify", "idle");
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Playlist download failed.");
        }

        await updateProgress();

        if (data.paused) {
            togglePlaybackButtons("spotify", "paused");
            showMessage("Download paused.", "info");
        } else {
            togglePlaybackButtons("spotify", "idle");
            showSuccess(`Downloaded ${data.completed} tracks.`);
        }
    } catch (error) {
        togglePlaybackButtons("spotify", "idle");
        showError(error.message);
    } finally {
        stopProgressPolling();
        document.getElementById("downloadBtn").disabled = false;
    }
}

async function stopDownload() {
    try {
        const response = await fetch("/api/stop", { method: "POST" });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Failed to pause the current download.");
        }

        document.getElementById("stopBtn").hidden = true;
        document.getElementById("resumeBtn").hidden = false;
        document.getElementById("stopYoutubePlaylistBtn").hidden = true;
        document.getElementById("resumeYoutubePlaylistBtn").hidden = false;
        showMessage(data.message, "info");
    } catch (error) {
        showError(error.message);
    }
}

function resumeDownload() {
    downloadPlaylist(true);
}

function startProgressPolling() {
    stopProgressPolling();
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
        const response = await fetch("/api/progress");
        const progress = await response.json();
        renderProgress(progress);

        if (progress.status === "paused") {
            document.getElementById("stopBtn").hidden = true;
            document.getElementById("resumeBtn").hidden = false;
            document.getElementById("stopYoutubePlaylistBtn").hidden = true;
            document.getElementById("resumeYoutubePlaylistBtn").hidden = false;
            stopProgressPolling();
        }

        if (progress.status === "completed" || progress.status === "error") {
            stopProgressPolling();
        }
    } catch (error) {
        console.error("Failed to update progress:", error);
    }
}

async function downloadYouTube() {
    const youtubeUrl = document.getElementById("youtubeUrl").value.trim();
    if (!youtubeUrl) {
        showError("Please enter a YouTube URL.");
        return;
    }

    const button = document.getElementById("youtubeDownloadBtn");
    button.disabled = true;
    button.textContent = "Downloading...";
    setInlineStatus("youtubeStatus", "Preparing your YouTube download...", "info");

    try {
        const response = await fetch("/api/youtube/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                youtube_url: youtubeUrl,
                download_to_device: downloadLocation === "device",
                format: document.querySelector('input[name="downloadFormat"]:checked').value,
            }),
        });

        if (downloadLocation === "device") {
            const blob = await response.blob();
            if (!response.ok) {
                throw new Error(await parseBlobError(blob));
            }

            const disposition = response.headers.get("Content-Disposition") || "";
            const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            const fallbackFormat = document.querySelector('input[name="downloadFormat"]:checked').value;
            const filename = match && match[1]
                ? match[1].replace(/['"]/g, "")
                : `youtube-download.${fallbackFormat}`;

            downloadBlob(blob, filename);
            setInlineStatus("youtubeStatus", `Downloaded to device: ${filename}`, "success");
            showSuccess("YouTube download complete.");
        } else {
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "YouTube download failed.");
            }

            setInlineStatus("youtubeStatus", data.message, "success");
            showSuccess("YouTube download complete.");
        }

        document.getElementById("youtubeUrl").value = "";
    } catch (error) {
        setInlineStatus("youtubeStatus", error.message, "error");
        showError(error.message);
    } finally {
        button.disabled = false;
        button.textContent = "Download";
    }
}

function setDownloadLocation(location) {
    downloadLocation = location;
    document.getElementById("serverToggle").classList.toggle("active", location === "server");
    document.getElementById("deviceToggle").classList.toggle("active", location === "device");
}

async function loadConfig() {
    try {
        const response = await fetch("/api/config");
        const config = await response.json();

        allowServerStorage = Boolean(config.allow_server_storage);
        const toggleSection = document.querySelector(".download-location-toggle");

        if (!allowServerStorage) {
            toggleSection.hidden = true;
            downloadLocation = "device";
            setDownloadLocation("device");
        } else {
            toggleSection.hidden = false;
            setDownloadLocation("device");
        }
    } catch (error) {
        console.error("Failed to load config:", error);
        downloadLocation = "device";
        setDownloadLocation("device");
    }
}

async function fetchYoutubePlaylist() {
    const playlistUrl = document.getElementById("youtubePlaylistUrl").value.trim();
    if (!playlistUrl) {
        showError("Please enter a YouTube playlist URL.");
        return;
    }

    const button = document.getElementById("fetchYoutubePlaylistBtn");
    button.disabled = true;
    button.textContent = "Fetching...";

    try {
        const response = await fetch("/api/youtube/playlist/info", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ playlist_url: playlistUrl }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to fetch YouTube playlist.");
        }

        displayYoutubePlaylistInfo(data.playlist);
        showSuccess("YouTube playlist loaded.");
    } catch (error) {
        showError(error.message);
    } finally {
        button.disabled = false;
        button.textContent = "Fetch Playlist";
    }
}

function displayYoutubePlaylistInfo(playlist) {
    const info = document.getElementById("youtubePlaylistInfo");
    const image = document.getElementById("youtubePlaylistImage");

    document.getElementById("youtubePlaylistName").textContent = playlist.name;
    document.getElementById("youtubePlaylistDescription").textContent = playlist.description || "No description provided.";
    document.getElementById("youtubeVideoCount").textContent = `${playlist.video_count} videos`;

    if (playlist.thumbnail) {
        image.src = playlist.thumbnail;
        image.hidden = false;
    } else {
        image.hidden = true;
        image.removeAttribute("src");
    }

    const list = document.getElementById("youtubeVideoList");
    list.innerHTML = "";

    playlist.videos.forEach((video, index) => {
        list.appendChild(createTrackRow(index, video.title, video.channel));
    });

    info.hidden = false;
    info.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function downloadYoutubePlaylist(resume = false) {
    const playlistUrl = document.getElementById("youtubePlaylistUrl").value.trim();
    if (!playlistUrl) {
        showError("Please enter a YouTube playlist URL.");
        return;
    }

    const progressSection = document.getElementById("progressSection");
    progressSection.hidden = false;
    if (!resume) {
        resetProgressPanel();
    }

    togglePlaybackButtons("youtubePlaylist", "downloading");
    startProgressPolling();

    try {
        const response = await fetch("/api/youtube/playlist/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                playlist_url: playlistUrl,
                resume,
                download_to_device: downloadLocation === "device",
                format: document.querySelector('input[name="youtubePlaylistFormat"]:checked').value,
            }),
        });

        if (downloadLocation === "device") {
            const blob = await response.blob();
            if (!response.ok) {
                throw new Error(await parseBlobError(blob));
            }

            downloadBlob(blob, "youtube-playlist.zip");
            await updateProgress();
            showSuccess("YouTube playlist archive downloaded to your device.");
            togglePlaybackButtons("youtubePlaylist", "idle");
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "YouTube playlist download failed.");
        }

        await updateProgress();

        if (data.paused) {
            togglePlaybackButtons("youtubePlaylist", "paused");
            showMessage("Download paused.", "info");
        } else {
            togglePlaybackButtons("youtubePlaylist", "idle");
            showSuccess(`Downloaded ${data.completed} videos.`);
        }
    } catch (error) {
        togglePlaybackButtons("youtubePlaylist", "idle");
        showError(error.message);
    } finally {
        stopProgressPolling();
        document.getElementById("downloadYoutubePlaylistBtn").disabled = false;
    }
}

function resumeYoutubePlaylist() {
    downloadYoutubePlaylist(true);
}

function setupPlaylistImport() {
    const fileInput = document.getElementById("playlistFile");
    const dropZone = document.getElementById("playlistDropZone");

    if (!fileInput || !dropZone) {
        return;
    }

    fileInput.addEventListener("change", () => {
        handlePlaylistFile(fileInput.files[0]);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.add("drag-over");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.remove("drag-over");
        });
    });

    dropZone.addEventListener("drop", (event) => {
        handlePlaylistFile(event.dataTransfer.files[0]);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadConfig();
    resetProgressPanel();
    setupPlaylistImport();

    const enterHandlers = [
        ["youtubeUrl", downloadYouTube],
        ["youtubePlaylistUrl", fetchYoutubePlaylist],
    ];

    enterHandlers.forEach(([elementId, handler]) => {
        const input = document.getElementById(elementId);
        if (!input) {
            return;
        }

        input.addEventListener("keypress", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                handler();
            }
        });
    });
});
