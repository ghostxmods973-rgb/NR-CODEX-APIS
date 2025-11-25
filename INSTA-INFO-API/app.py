from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

@app.route('/insta-info', methods=['GET'])
def insta_info():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Missing 'username' parameter"}), 400

    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch profile"}), 404

        soup = BeautifulSoup(response.text, 'html.parser')

        # Get page title: usually like "Cristiano Ronaldo (@cristiano) • Instagram photos and videos"
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else ""

        # Get meta description (has follower count, following, and bio preview)
        desc = soup.find("meta", attrs={"name": "description"})
        desc_content = desc["content"] if desc else ""

        # Parse followers/following from meta description
        match = re.search(r'([\d.,]+)\sFollowers?,\s([\d.,]+)\sFollowing', desc_content)
        followers = match.group(1) if match else None
        following = match.group(2) if match else None

        # Extract full bio (if available in description meta tag or visible in profile)
        bio = None
        bio_tag = soup.find("meta", attrs={"property": "og:description"})
        if bio_tag:
            bio = bio_tag["content"]

        # Extract total posts, reels, and links from page
        posts_reels_links = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)},"edge_felix_video_media":{"count":(\d+)},"external_url":"([^"]+)"', response.text)
        total_posts = posts_reels_links.group(1) if posts_reels_links else None
        total_reels = posts_reels_links.group(2) if posts_reels_links else None
        external_url = posts_reels_links.group(3) if posts_reels_links else None

        # Extract profile picture
        profile_pic = re.search(r'"profile_pic_url_hd":"([^"]+)"', response.text)
        profile_pic_url = profile_pic.group(1).replace("\\u0026", "&") if profile_pic else None

        return jsonify({
            "username": username,
            "title": title,
            "followers": followers,
            "following": following,
            "bio": bio,
            "total_posts": total_posts,
            "total_reels": total_reels,
            "profile_pic": profile_pic_url,
            "external_url": external_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Required for Vercel (entrypoint)
handler = app
