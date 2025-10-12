from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/checkbanned', methods=['GET'])
def check_banned():
    try:
        player_id = request.args.get('id')
        if not player_id:
            return jsonify({"error": "Player ID is required"}), 400

        # Step 1: Fetch ban status from Garena's anti-hack API
        garena_url = f"https://ff.garena.com/api/antihack/check_banned?lang=en&uid={player_id}"
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json, text/plain, */*",
            'authority': "ff.garena.com",
            'accept-language': "en-GB,en-US;q=0.9,en;q=0.8",
            'referer': "https://ff.garena.com/en/support/",
            'sec-ch-ua': "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\"",
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': "\"Android\"",
            'sec-fetch-dest': "empty",
            'sec-fetch-mode': "cors",
            'sec-fetch-site': "same-origin",
            'x-requested-with': "B6FksShzIgjfrYImLpTsadjS86sddhFH",
            'Cookie': "_ga_8RFDT0P8N9=GS1.1.1706295767.2.0.1706295767.0.0.0; apple_state_key=8236785ac31b11ee960a621594e13693; datadome=bbC6XTzUAS0pXgvEs7u",
        }

        garena_response = requests.get(garena_url, headers=headers)
        ban_data = {}
        if garena_response.status_code == 200:
            ban_data = garena_response.json()
        else:
            ban_data = {"error": "Failed to fetch ban data from Garena server"}

        # Step 2: Fetch nickname, region, and level from the new REGIONAPI
        region_api_url = f"https://nr-codex-apis.onrender.com/REGION-API/check?uid={player_id}"
        region_response = requests.get(region_api_url)
        region_data = {}
        if region_response.status_code == 200:
            region_data = region_response.json()
        else:
            region_data = {"error": "Failed to fetch data from REGIONAPI"}

        # Step 3: Combine responses
        is_banned = ban_data.get('data', {}).get('is_banned', 0)
        period = ban_data.get('data', {}).get('period', 0)
        
        # Extract nickname, region, and level from REGIONAPI response
        nickname = region_data.get('formatted_response', {}).get('nickname', None)
        region = region_data.get('formatted_response', {}).get('region', None)
        level = region_data.get('raw_api_response', {}).get('basicInfo', {}).get('level', None)

        response = {
            "player_id": player_id,
            "is_banned": bool(is_banned),
            "ban_period": period if is_banned else 0,
            "status": "BANNED" if is_banned else "NOT BANNED",
            "nickname": nickname,
            "region": region,
            "level": level
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_key', methods=['GET'])
def check_key():
    return jsonify({
        "status": "no_key_required",
        "message": "This API does not require an API key for access"
    }), 200

import sys

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting {__name__.upper()} on port {port} ...")
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    app.run(host='0.0.0.0', port=port, debug=False)
