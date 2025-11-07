# ------------------------------------------------------------
# YouTube Advanced Info API — Credit: Anmol (@FOREVER_HIDDEN)
# JOIN : @SOURCE_SUTRA FOR MORE SRC | API | BOT CODE | METHOD | 🛐
# Purpose: Get full YouTube channel info + latest video + live status
# ------------------------------------------------------------

from flask import Flask, jsonify, request
import requests
import datetime

app = Flask(__name__)

YOUTUBE_API_KEY = "AIzaSyBEiPn1vJDnu7oRbT9XH0v2SPdvUnHqN0k"


def get_channel_id(name_or_id):
    """Detect if input is ID or Name and return valid channel ID"""
    if name_or_id.startswith("UC"):
        return name_or_id

    # Search by channel name
    search_url = (
        f"https://www.googleapis.com/youtube/v3/search?part=id&type=channel&q={name_or_id}&key={YOUTUBE_API_KEY}"
    )
    resp = requests.get(search_url)
    data = resp.json()
    if data.get("items"):
        return data["items"][0]["id"]["channelId"]
    return None


def get_channel_info(channel_id):
    """Fetch channel details"""
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id={channel_id}&key={YOUTUBE_API_KEY}"
    r = requests.get(url)
    return r.json()


def get_recent_videos(channel_id):
    """Fetch latest 8 videos"""
    url = (
        f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}"
        f"&channelId={channel_id}&part=snippet,id&order=date&maxResults=8"
    )
    r = requests.get(url)
    return r.json()


def check_live_status(channel_id):
    """Check if channel is currently live"""
    url = (
        f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}"
        f"&eventType=live&type=video&key={YOUTUBE_API_KEY}"
    )
    r = requests.get(url)
    data = r.json()
    if data.get("items"):
        live_vid = data["items"][0]
        vid = live_vid["id"]["videoId"]
        return {
            "status": "LIVE 🔴",
            "video_id": vid,
            "title": live_vid["snippet"]["title"],
            "url": f"https://youtu.be/{vid}"
        }
    return {"status": "OFFLINE ⚫"}


@app.route("/api/yt", methods=["GET"])
def yt_api():
    query = request.args.get("channel")
    if not query:
        return jsonify({"error": "Missing parameter 'channel'"}), 400

    channel_id = get_channel_id(query)
    if not channel_id:
        return jsonify({"error": "Channel not found"}), 404

    try:
        info = get_channel_info(channel_id)
        if not info.get("items"):
            return jsonify({"error": "No channel data"}), 404

        ch = info["items"][0]
        snippet = ch["snippet"]
        stats = ch["statistics"]

        out = {
            "channel_id": channel_id,
            "channel_name": snippet.get("title"),
            "description": snippet.get("description"),
            "country": snippet.get("country"),
            "creation_date": snippet.get("publishedAt"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "subscribers": stats.get("subscriberCount"),
            "views": stats.get("viewCount"),
            "videos": stats.get("videoCount"),
        }

        # Live status check
        live_data = check_live_status(channel_id)
        out["live_status"] = live_data["status"]
        if live_data["status"] == "LIVE 🔴":
            out["live_video"] = live_data

        # Recent uploads
        recents = get_recent_videos(channel_id)
        vids = []
        last_video_date = None
        for v in recents.get("items", []):
            vid = v.get("id", {}).get("videoId")
            if not vid:
                continue
            sn = v["snippet"]
            vids.append({
                "video_id": vid,
                "title": sn.get("title"),
                "published_at": sn.get("publishedAt"),
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url"),
                "url": f"https://youtu.be/{vid}"
            })

            # Track most recent video date
            if not last_video_date:
                last_video_date = sn.get("publishedAt")

        out["recent_videos"] = vids
        out["last_video_date"] = last_video_date

        return jsonify(out)

    except Exception as e:
        return jsonify({"error": "internal_error", "details": str(e)}), 500

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting JWT-API on port {port} ...")
    
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    
    app.run(host='0.0.0.0', port=port, debug=False)
  
