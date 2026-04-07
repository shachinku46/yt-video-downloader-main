from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import os
import uuid
import threading
import imageio_ffmpeg

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

progress_data = {}

# ✅ FFmpeg from imageio (Render compatible)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- VIDEO INFO ----------------
@app.route("/info")
def info():
    url = request.args.get("url")

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            data = ydl.extract_info(url, download=False)

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "uploader": data.get("uploader"),
            "duration": data.get("duration_string")
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- DOWNLOAD THREAD ----------------
def download_task(url, file_id, format_type):

    def hook(d):
        if d['status'] == 'downloading':
            progress_data[file_id] = {
                "percent": d.get('_percent_str', '0%').strip(),
                "speed": d.get('_speed_str', '')
            }
        elif d['status'] == 'finished':
            progress_data[file_id] = {
                "percent": "100%",
                "speed": "Processing..."
            }

    try:
        if format_type == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/{file_id}.%(ext)s',
                'ffmpeg_location': FFMPEG_PATH,
                'progress_hooks': [hook],
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

        else:
            # ✅ SAFE FORMAT (NO ERROR)
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/{file_id}.%(ext)s',
                'ffmpeg_location': FFMPEG_PATH,
                'progress_hooks': [hook],
                'noplaylist': True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        progress_data[file_id] = {"percent": "error", "speed": str(e)}


# ---------------- START DOWNLOAD ----------------
@app.route("/download", methods=["POST"])
def download():
    data = request.json

    url = data.get("url")
    format_type = data.get("type")

    file_id = str(uuid.uuid4())
    progress_data[file_id] = {"percent": "0%", "speed": ""}

    threading.Thread(target=download_task, args=(url, file_id, format_type)).start()

    return jsonify({"id": file_id})


# ---------------- PROGRESS ----------------
@app.route("/progress/<file_id>")
def progress(file_id):
    return jsonify(progress_data.get(file_id, {"percent": "0%", "speed": ""}))


# ---------------- DOWNLOAD FILE ----------------
@app.route("/file/<file_id>")
def file(file_id):
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.startswith(file_id):
            return send_from_directory(DOWNLOAD_FOLDER, f, as_attachment=True)
    return "File not found"


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
