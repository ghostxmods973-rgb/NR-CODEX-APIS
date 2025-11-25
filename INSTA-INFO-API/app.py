import httpx
from flask import Flask, jsonify

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 Chrome/118.0 Safari/537.36"
}

BASE1 = "https://www.instagram.com/api/v1/users/web_profile_info/?username="
BASE2 = "https://i.instagram.com/api/v1/users/web_profile_info/?username="
MEDIA_API = "https://www.instagram.com/graphql/query/?query_hash=e769aa130647d2354c40ea6a439bfc08&variables="

def get_profile(username):
    urls = [BASE1 + username, BASE2 + username]
    for u in urls:
        try:
            r = httpx.get(u, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return r.json()
        except:
            pass
    return None

def get_recent_posts(user_id):
    payload = {"id": user_id, "first": 12}
    url = MEDIA_API + httpx.QueryParams(payload).to_str()
    try:
        r = httpx.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        return None

@app.route("/api/insta/<username>", methods=["GET"])
def insta(username):
    profile = get_profile(username)
    if not profile:
        return jsonify({"error": "profile_not_found"}), 404

    user = profile.get("data", {}).get("user", {})
    if not user:
        return jsonify({"error": "invalid_profile"}), 404

    user_id = user.get("id")
    posts = get_recent_posts(user_id)

    return jsonify({
        "status": "success",
        "user_id": user_id,
        "username": user.get("username"),
        "full_name": user.get("full_name"),
        "bio": user.get("biography"),
        "is_private": user.get("is_private"),
        "is_verified": user.get("is_verified"),
        "followers": user.get("edge_followed_by", {}).get("count"),
        "following": user.get("edge_follow", {}).get("count"),
        "profile_pic": user.get("profile_pic_url_hd"),
        "recent_posts": posts
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
