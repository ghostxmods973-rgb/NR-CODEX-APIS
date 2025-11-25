import os
import sys
import subprocess

# ==============================
# AUTO INSTALL MISSING PACKAGES
# ==============================
required = ["flask", "requests"]

def auto_install():
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[AUTO-INSTALL] Installing {pkg} ...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg])

auto_install()

# ==============================
#   MAIN APPLICATION
# ==============================
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)


# Convert numbers to K/M (e.g. 274M)
def format_num(n):
    if n is None:
        return None
    if n >= 1_000_000:
        return f"{round(n / 1_000_000, 1)}M"
    if n >= 1_000:
        return f"{round(n / 1_000, 1)}K"
    return str(n)


@app.route("/insta-info", methods=["GET"])
def insta_info():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Missing username"}), 400

    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-IG-App-ID": "936619743392459",   # Public app ID (no login required)
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return jsonify({"error": "Profile not found"}), 404

        user = r.json().get("data", {}).get("user", {})

        followers_raw = user.get("edge_followed_by", {}).get("count")
        following_raw = user.get("edge_follow", {}).get("count")

        return jsonify({
            "status": "success",
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "bio": user.get("biography"),
            "followers": followers_raw,
            "followers_short": format_num(followers_raw),
            "following": following_raw,
            "following_short": format_num(following_raw),
            "total_posts": user.get("edge_owner_to_timeline_media", {}).get("count"),
            "profile_pic": user.get("profile_pic_url_hd"),
            "external_url": user.get("external_url"),
            "is_private": user.get("is_private"),
            "is_verified": user.get("is_verified")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting JWT-API on port {port} ...")
    
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    
    app.run(host='0.0.0.0', port=port, debug=False)
