# ------------------------------------------------------------
# Instagram Info API — FIXED & CLEAN 2025 VERSION
# Author: Anmol (@FOREVER_HIDDEN)
# ------------------------------------------------------------

from flask import Flask, jsonify, request
import requests
import time
from functools import lru_cache
import json

app = Flask(__name__)

INSTAGRAM_SNAPSHOT = "https://www.instagram.com/{}/?__a=1&__d=dis"

@lru_cache(maxsize=1024)
def fetch_profile(username, proxy=None):
    url = INSTAGRAM_SNAPSHOT.format(username)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 11; RMX) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": f"https://www.instagram.com/{username}/",
    }

    proxies = {"http": proxy, "https": proxy} if proxy else None

    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, proxies=proxies, timeout=10)

            if r.status_code == 200:
                try:
                    return r.json()
                except:
                    if "graphql" in r.text:
                        start = r.text.find("{")
                        end = r.text.rfind("}") + 1
                        raw = r.text[start:end]
                        return json.loads(raw)

            if r.status_code in (401, 429, 403):
                time.sleep(1)
                continue

            if r.status_code == 404:
                return {"error": "not_found"}

        except Exception:
            time.sleep(1)

    return {"error": "failed"}

@app.route("/api/insta/<username>")
def insta(username):
    proxy = request.args.get("proxy")
    data = fetch_profile(username, proxy)

    if "error" in data:
        return jsonify(data)

    try:
        g = data.get("graphql", {}).get("user")
        if not g:
            return jsonify({"error": "parse_failed", "raw": data})

        out = {
            "id": g.get("id"),
            "username": g.get("username"),
            "full_name": g.get("full_name"),
            "biography": g.get("biography"),
            "is_private": g.get("is_private"),
            "is_verified": g.get("is_verified"),
            "profile_pic_url": g.get("profile_pic_url_hd") or g.get("profile_pic_url"),
            "followers_count": g.get("edge_followed_by", {}).get("count"),
            "following_count": g.get("edge_follow", {}).get("count"),
            "media_count": g.get("edge_owner_to_timeline_media", {}).get("count"),
            "recent_media": []
        }

        edges = g.get("edge_owner_to_timeline_media", {}).get("edges", [])
        for e in edges[:8]:
            node = e.get("node", {})

            caption = None
            cap = node.get("edge_media_to_caption", {}).get("edges", [])
            if cap:
                caption = cap[0]["node"].get("text")

            out["recent_media"].append({
                "id": node.get("id"),
                "shortcode": node.get("shortcode"),
                "display_url": node.get("display_url"),
                "taken_at": node.get("taken_at_timestamp"),
                "caption": caption
            })

        return jsonify(out)

    except Exception as exc:
        return jsonify({"error": "parse_error", "details": str(exc), "raw": data})


# ------------------- START SERVER (NO ERROR NOW) -------------------
if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting INSTAGRAM API on port {port} ...")

    app.run(host='0.0.0.0', port=port, debug=False)
