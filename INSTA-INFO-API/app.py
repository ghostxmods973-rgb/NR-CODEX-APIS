from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def extract_number(text):
    """Convert 1.2M → 1200000, 3.4K → 3400"""
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
        return jsonify({"error": "Missing 'username' parameter"}), 400

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

        # -------------------------
        # TITLE
        # -------------------------
        title = soup.title.text.strip() if soup.title else ""

        # -------------------------
        # META DESCRIPTION (followers/following)
        # -------------------------
        desc = soup.find("meta", attrs={"name": "description"})
        desc_content = desc["content"] if desc else ""

        match = re.search(r'([\d.,KM]+)\sFollowers?,\s([\d.,KM]+)\sFollowing', desc_content)
        followers = extract_number(match.group(1)) if match else None
        following = extract_number(match.group(2)) if match else None

        # -------------------------
        # BIO
        # -------------------------
        bio_meta = soup.find("meta", property="og:description")
        bio = bio_meta["content"] if bio_meta else None
        if bio and "• Instagram photos" in bio:
            bio = None  # remove Instagram auto text

        # -------------------------
        # POSTS / REELS / URL
        # -------------------------
        posts = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', r.text)
        reels = re.search(r'"edge_felix_video_media":{"count":(\d+)}', r.text)
        external = re.search(r'"external_url":"([^"]+)"', r.text)

        total_posts = posts.group(1) if posts else None
        total_reels = reels.group(1) if reels else None
        external_url = external.group(1).replace("\\u0026", "&") if external else None

        # -------------------------
        # PROFILE PIC
        # -------------------------
        pfp = re.search(r'"profile_pic_url_hd":"([^"]+)"', r.text)
        profile_pic = pfp.group(1).replace("\\u0026", "&") if pfp else None

        return jsonify({
            "status": "success",
            "username": username,
            "title": title,
            "followers": followers,
            "following": following,
            "total_posts": total_posts,
            "total_reels": total_reels,
            "bio": bio,
            "profile_pic": profile_pic,
            "external_url": external_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# For Vercel (export as handler)
handler =app
# ===================== STARTUP / MAIN =====================
if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting JWT-API on port {port} ...")

    # Start the background token updater thread
    start_token_updater_thread()

    # Start Flask
    # Use 0.0.0.0 so container/remote can access if needed
    app.run(host='0.0.0.0', port=port, debug=False)
    
