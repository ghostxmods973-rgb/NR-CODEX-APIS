import os
import sys
import subprocess

# ==========================
# AUTO INSTALL MISSING LIBS
# ==========================
required = [
    "flask",
    "requests",
    "beautifulsoup4",
    "lxml",
]

def install_missing():
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            print(f"[AUTO-INSTALL] Installing {pkg} ...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg])

install_missing()

# ==========================
# ACTUAL APPLICATION STARTS
# ==========================
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)


def extract_number(text):
    if not text:
        return None
    text = text.replace(",", "")
    if "M" in text:
        return int(float(text.replace("M", "")) * 1_000_000)
    if "K" in text:
        return int(float(text.replace("K", "")) * 1_000)
    return int(re.sub(r"\D", "", text))


@app.route("/insta-info", methods=["GET"])
def insta_info():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Missing 'username'"}), 400

    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return jsonify({"error": "Profile not found"}), 404

        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.text.strip() if soup.title else ""

        desc = soup.find("meta", {"name": "description"})
        desc_content = desc["content"] if desc else ""

        match = re.search(r'([\d.,KM]+)\sFollowers?,\s([\d.,KM]+)\sFollowing', desc_content)
        followers = extract_number(match.group(1)) if match else None
        following = extract_number(match.group(2)) if match else None

        bio_tag = soup.find("meta", property="og:description")
        bio = bio_tag["content"] if bio_tag else None
        if bio and "• Instagram photos" in bio:
            bio = None

        posts = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', r.text)
        reels = re.search(r'"edge_felix_video_media":{"count":(\d+)}', r.text)
        external = re.search(r'"external_url":"([^"]+)"', r.text)
        pfp = re.search(r'"profile_pic_url_hd":"([^"]+)"', r.text)

        return jsonify({
            "status": "success",
            "username": username,
            "title": title,
            "followers": followers,
            "following": following,
            "total_posts": posts.group(1) if posts else None,
            "total_reels": reels.group(1) if reels else None,
            "bio": bio,
            "profile_pic": pfp.group(1).replace("\\u0026", "&") if pfp else None,
            "external_url": external.group(1).replace("\\u0026", "&") if external else None,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"🚀 Running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
