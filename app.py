from flask import Flask, render_template, request, redirect
import requests
import os
import re

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

RAPIDAPI_KEY = "f30b4baaecmsh7d04f39e3f19019p15339bjsnad800cd8c0d2"
RAPIDAPI_HOST = "yt-api.p.rapidapi.com"

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

def extract_video_id(url):
    patterns = [
        r'(?:v=)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_data(url):
    video_id = extract_video_id(url)
    if not video_id:
        print("Video ID tidak ditemukan")
        return None

    print(f"Video ID: {video_id}")

    try:
        # Ambil info video
        r = requests.get(
            f"https://{RAPIDAPI_HOST}/video/info",
            params={"id": video_id},
            headers=HEADERS,
            timeout=20
        )
        print(f"Info status: {r.status_code}")
        print(f"Info response: {r.text[:500]}")
        info = r.json()

        title = info.get("title", "YouTube Video")
        duration = info.get("lengthSeconds", "")
        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

        if duration:
            try:
                secs = int(duration)
                duration = f"{secs//60}:{secs%60:02d}"
            except:
                duration = ""

        # Ambil link download
        r2 = requests.get(
            f"https://{RAPIDAPI_HOST}/dl",
            params={"id": video_id, "cgeo": "US"},
            headers=HEADERS,
            timeout=20
        )
        print(f"DL status: {r2.status_code}")
        print(f"DL response: {r2.text[:500]}")
        dl_data = r2.json()

        qualities = []
        audio_url = None

        formats = dl_data.get("formats") or dl_data.get("adaptiveFormats") or []
        for fmt in formats:
            mime = fmt.get("mimeType", "")
            quality = fmt.get("qualityLabel") or fmt.get("quality", "")
            url_fmt = fmt.get("url", "")
            if "video/mp4" in mime and quality and url_fmt:
                qualities.append({"quality": quality, "url": url_fmt})
            elif "audio" in mime and url_fmt and not audio_url:
                audio_url = url_fmt

        order = {"1080p": 0, "720p": 1, "480p": 2, "360p": 3, "240p": 4, "144p": 5}
        qualities.sort(key=lambda x: order.get(x["quality"], 99))

        video_url = qualities[0]["url"] if qualities else dl_data.get("url")
        if not audio_url:
            audio_url = dl_data.get("audioUrl")

        return {
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "video": video_url,
            "qualities": qualities[:4],
            "audio": audio_url
        }

    except Exception as e:
        print(f"Error: {e}")
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        input_url = request.form.get("url", "").strip()
        if not input_url or ("youtube.com" not in input_url and "youtu.be" not in input_url):
            error = "Masukkan link YouTube yang valid."
        else:
            result = get_youtube_data(input_url)
            if not result:
                error = "Gagal memproses video. Pastikan link benar dan coba lagi."
    return render_template("index.html", result=result, error=error)

@app.route("/download")
def download():
    video_url = request.args.get("url")
    dl_type = request.args.get("type", "video")
    if not video_url:
        return "URL tidak valid", 400
    try:
        r = requests.get(
            video_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.youtube.com/",
                "Origin": "https://www.youtube.com",
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Range": "bytes=0-"
            },
            stream=True,
            timeout=25
        )
        ext = "mp3" if dl_type == "mp3" else "mp4"
        content_type = "audio/mpeg" if dl_type == "mp3" else "video/mp4"
        filename = f"YTSave_{int(time.time())}.{ext}"

        def generate():
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        return Response(generate(), headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type,
            "Cache-Control": "no-cache",
        })
    except Exception as e:
        print(f"Download error: {e}")
        return redirect(video_url)


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

if __name__ == "__main__":
    app.run(debug=True)
