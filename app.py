from flask import Flask, render_template, request, jsonify
import yt_dlp

app = Flask(__name__)

# Home page
@app.route('/')
def index():
    return render_template('index.html')


# Preview video
@app.route('/preview', methods=['POST'])
def preview():
    url = request.form.get('url')

    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']   # 🔥 IMPORTANT FIX
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail')
        })

    except Exception as e:
        return jsonify({'error': str(e)})


# Download video/mp3
@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_type = request.form.get('format')  # video or mp3

    try:
        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'noplaylist': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android']
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0'
                },
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }

        else:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',  # 🔥 FIXED FORMAT
                'quiet': True,
                'noplaylist': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android']
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0'
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
