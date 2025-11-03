import httpx
import json
from flask import Flask, request, jsonify
from datetime import datetime
import urllib.parse

app = Flask(__name__)

@app.route('/info', methods=['GET'])
def get_map_info():
    """
    Get Free Fire Map Share information
    Usage: /info?map_code=23FREEFIRE435DE8FA485D44460958106964C620FC4781&region=ind
    """
    
    map_code = request.args.get('map_code')
    region = request.args.get('region', 'IND').upper()
    lang = request.args.get('lang', 'en').lower()
    
    if not map_code:
        return jsonify({
            "code": 400,
            "status": "error",
            "msg": "map_code is required",
            "data": None
        }), 400
    
    # Remove # if present and ensure proper format
    if map_code.startswith('23FREEFIRE'):
        map_code = map_code
    elif map_code.startswith('#'):
        map_code = map_code[1:]
    else:
        map_code = map_code
    
    # Prepare the API URL
    encoded_map_code = f"%23{map_code}"  # URL encode the #
    device_id = "4e93e5106b39e1902e24d1ba2f17c709"  # Static device ID
    
    url = f"https://mapshare.freefiremobile.com/api/info?lang={lang}&region={region}&map_code={encoded_map_code}&device_id={device_id}"
    
    try:
        # Make request to Free Fire API
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
        
        if response.status_code != 200:
            return jsonify({
                "code": response.status_code,
                "status": "error",
                "msg": f"API returned status {response.status_code}",
                "data": None
            }), response.status_code
        
        data = response.json()
        
        # If the API returns success, format the response
        if data.get("code") == 0:
            return jsonify({
                "code": 0,
                "status": "success",
                "msg": "",
                "data": {
                    "map_info": {
                        "workshop_code": data["data"]["workshop_code_info"]["workshop_code"],
                        "author_name": data["data"]["workshop_code_info"]["author_name"],
                        "map_name": data["data"]["workshop_code_info"]["workshop_name"],
                        "description": data["data"]["workshop_code_info"]["workshop_desc"],
                        "team_count": data["data"]["workshop_code_info"]["team_count"],
                        "game_mode": data["data"]["workshop_code_info"]["game_mode"],
                        "subscribe_count": data["data"]["workshop_code_info"]["subscribe_count"],
                        "like_count": data["data"]["workshop_code_info"]["like_count"],
                        "estimated_play_time": f"{data['data']['workshop_code_info']['min_est_play_time']} seconds",
                        "tags": data["data"]["workshop_code_info"]["tags"]
                    },
                    "game_info": {
                        "title": data["data"]["title"],
                        "game_name": data["data"]["game_name"],
                        "region": data["data"]["region"],
                        "language": data["data"]["lang"],
                        "android_download": data["data"]["android_download_url"],
                        "ios_download": data["data"]["ios_download_url"],
                        "ugc_url": data["data"]["ugc_url"]
                    },
                    "images": {
                        "backgrounds": data["data"]["imgs"],
                        "game_icon": data["data"]["game_icon"],
                        "share_image": data["data"]["share_img"]
                    },
                    "timestamps": {
                        "start_time": data["data"]["start_time"],
                        "end_time": data["data"]["end_time"],
                        "start_time_formatted": convert_timestamp(data["data"]["start_time"]),
                        "end_time_formatted": convert_timestamp(data["data"]["end_time"])
                    }
                }
            })
        else:
            return jsonify({
                "code": data.get("code", 500),
                "status": "error",
                "msg": data.get("msg", "Unknown error"),
                "data": None
            }), 500
            
    except httpx.RequestError as e:
        return jsonify({
            "code": 503,
            "status": "error",
            "msg": f"Network error: {str(e)}",
            "data": None
        }), 503
    except json.JSONDecodeError as e:
        return jsonify({
            "code": 500,
            "status": "error",
            "msg": f"Invalid JSON response: {str(e)}",
            "data": None
        }), 500
    except Exception as e:
        return jsonify({
            "code": 500,
            "status": "error",
            "msg": f"Server error: {str(e)}",
            "data": None
        }), 500

@app.route('/map_details', methods=['GET'])
def get_map_details():
    """
    Get detailed map information with translations
    Usage: /map_details?map_code=23FREEFIRE435DE8FA485D44460958106964C620FC4781&region=ind
    """
    
    map_code = request.args.get('map_code')
    region = request.args.get('region', 'IND').upper()
    lang = request.args.get('lang', 'en').lower()
    
    if not map_code:
        return jsonify({"error": "map_code is required"}), 400
    
    # Prepare the API URL
    if map_code.startswith('#'):
        encoded_map_code = f"%23{map_code[1:]}"
    else:
        encoded_map_code = f"%23{map_code}"
    
    device_id = "4e93e5106b39e1902e24d1ba2f17c709"
    url = f"https://mapshare.freefiremobile.com/api/info?lang={lang}&region={region}&map_code={encoded_map_code}&device_id={device_id}"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
        
        if response.status_code != 200:
            return jsonify({"error": f"API returned status {response.status_code}"}), response.status_code
        
        data = response.json()
        
        if data.get("code") == 0:
            workshop_info = data["data"]["workshop_code_info"]
            game_config = data["data"]["game_config"]
            
            # Extract tags with translations
            tags_with_names = []
            for tag_id in workshop_info.get("tags", []):
                tag_info = next((tag for tag in game_config["show_tag_options_flat"] if tag["id"] == tag_id), None)
                if tag_info:
                    tag_name = game_config["translations"].get(tag_info["tag_key"], tag_info["tag_key"])
                    tags_with_names.append({
                        "id": tag_id,
                        "key": tag_info["tag_key"],
                        "name": tag_name,
                        "type": tag_info["tag_type"]
                    })
            
            # Get game mode name
            game_mode_id = workshop_info.get("game_mode")
            game_mode_name = game_config["translations"].get(
                game_config["game_mode_id_key_map"].get(str(game_mode_id), f"Unknown Mode {game_mode_id}")
            )
            
            # Get mode template name
            mode_template_id = workshop_info.get("mode_template_id")
            mode_template_name = game_config["translations"].get(
                game_config["mode_template_id_key_map"].get(str(mode_template_id), f"Unknown Template {mode_template_id}")
            )
            
            return jsonify({
                "code": 0,
                "status": "success",
                "data": {
                    "basic_info": {
                        "workshop_code": workshop_info["workshop_code"],
                        "map_name": workshop_info["workshop_name"],
                        "author": workshop_info["author_name"],
                        "description": workshop_info["workshop_desc"],
                        "short_description": workshop_info.get("sub_desc", "")
                    },
                    "gameplay_info": {
                        "team_count": workshop_info["team_count"],
                        "group_mode": workshop_info["group_mode"],
                        "game_mode": {
                            "id": game_mode_id,
                            "name": game_mode_name
                        },
                        "mode_template": {
                            "id": mode_template_id,
                            "name": mode_template_name
                        },
                        "round_count": workshop_info.get("round_count", 1),
                        "map_id": workshop_info.get("map_id"),
                        "estimated_play_time": f"{workshop_info['min_est_play_time']} - {workshop_info['max_est_play_time']} seconds"
                    },
                    "social_info": {
                        "subscribe_count": workshop_info["subscribe_count"],
                        "like_count": workshop_info["like_count"],
                        "map_cover_url": workshop_info.get("map_cover_url", "")
                    },
                    "tags": tags_with_names,
                    "download_info": {
                        "android": data["data"]["android_download_url"],
                        "ios": data["data"]["ios_download_url"],
                        "ugc_portal": data["data"]["ugc_url"]
                    },
                    "region_info": {
                        "region": data["data"]["region"],
                        "language": data["data"]["lang"],
                        "region_lang": data["data"]["region_lang"]
                    }
                }
            })
        else:
            return jsonify({
                "code": data.get("code", 500),
                "status": "error",
                "msg": data.get("msg", "Unknown error")
            }), 500
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "status": "error",
            "msg": f"Server error: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "service": "Free Fire Map Share API",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/info": "Get basic map information",
            "/map_details": "Get detailed map information",
            "/health": "Health check"
        }
    })

def convert_timestamp(timestamp):
    """Convert timestamp to readable format"""
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Invalid timestamp"

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting JWT-API on port {port} ...")
    
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    
    app.run(host='0.0.0.0', port=port, debug=False)
    
