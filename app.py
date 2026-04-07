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

FFMPEG_PATH = "ffmpeg"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/info")
def info():
    url = request.args.get("url")

    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt'   # ✅ important
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "uploader": data.get("uploader"),
            "duration": data.get("duration_string")
        })

    except Exception as e:
        return jsonify({"error": str(e)})


def download_task(url, file_id, format_type, quality):

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
                'quiet': True,
                'noplaylist': True,
                'cookiefile': 'cookies.txt',

                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
            }

        else:
            fmt = "bestvideo+bestaudio/best" if quality == "max" else f"bestvideo[height<={quality}]+bestaudio/best"

            ydl_opts = {
                'format': fmt,
                'outtmpl': f'{DOWNLOAD_FOLDER}/{file_id}.%(ext)s',
                'ffmpeg_location': FFMPEG_PATH,
                'progress_hooks': [hook],
                'quiet': True,
                'noplaylist': True,
                'cookiefile': 'cookies.txt',
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        progress_data[file_id] = {"percent": "error", "speed": str(e)}


@app.route("/download", methods=["POST"])
def download():
    data = request.json

    file_id = str(uuid.uuid4())
    progress_data[file_id] = {"percent": "0%", "speed": ""}

    threading.Thread(
        target=download_task,
        args=(data.get("url"), file_id, data.get("type"), data.get("quality"))
    ).start()

    return jsonify({"id": file_id})


@app.route("/progress/<file_id>")
def progress(file_id):
    return jsonify(progress_data.get(file_id, {"percent": "0%", "speed": ""}))


@app.route("/file/<file_id>")
def file(file_id):
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.startswith(file_id):
            return send_from_directory(DOWNLOAD_FOLDER, f, as_attachment=True)
    return "File not found"


if __name__ == "__main__":
    app.run(debug=True)
