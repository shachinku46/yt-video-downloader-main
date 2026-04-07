from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

progress_data = {}

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- VIDEO INFO ----------------
@app.route("/info")
def info():
    url = request.args.get("url")

    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for f in data.get("formats", []):
            if f.get("height"):
                h = f.get("height")

                if h not in seen:
                    seen.add(h)
                    formats.append({
                        "quality": f"{h}p",
                        "height": h
                    })

        formats = sorted(formats, key=lambda x: x["height"], reverse=True)

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "formats": formats
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- DOWNLOAD THREAD ----------------
def download_task(url, file_id, format_type, quality):

    def hook(d):
        if d['status'] == 'downloading':
            progress_data[file_id] = {
                "percent": d.get('_percent_str', '0%'),
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
                'progress_hooks': [hook],
                'cookiefile': 'cookies.txt',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
            }

        else:
            # 🔥 ULTRA SAFE FORMAT (NEVER FAILS)
            fmt = f"best[height<={quality}]/best"

            ydl_opts = {
                'format': fmt,
                'outtmpl': f'{DOWNLOAD_FOLDER}/{file_id}.%(ext)s',
                'progress_hooks': [hook],
                'cookiefile': 'cookies.txt'
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
    quality = data.get("quality")

    file_id = str(uuid.uuid4())

    progress_data[file_id] = {"percent": "0%", "speed": ""}

    threading.Thread(target=download_task, args=(url, file_id, format_type, quality)).start()

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


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
