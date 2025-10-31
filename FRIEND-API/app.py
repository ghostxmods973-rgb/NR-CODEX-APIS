from flask import Flask, request, jsonify
import jwt
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import RemoveFriend_Req_pb2
from byte import Encrypt_ID, encrypt_api
import binascii
import data_pb2
import uid_generator_pb2
import my_pb2
import output_pb2
from datetime import datetime
import json
import time
import urllib3
import warnings

# -----------------------------
# Security Warnings Disable
# -----------------------------
# HTTPS warnings disable karo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UserWarning, message="Unverified HTTPS request")

app = Flask(__name__)

# -----------------------------
# AES Configuration
# -----------------------------
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def encrypt_message(data_bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data_bytes, AES.block_size))

def encrypt_message_hex(data_bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(data_bytes, AES.block_size))
    return binascii.hexlify(encrypted).decode('utf-8')

# -----------------------------
# Region-based URL Configuration
# -----------------------------
def get_base_url(server_name):
    server_name = server_name.upper()
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com/"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/"
    else:
        return "https://clientbp.ggblueshark.com/"

def get_server_from_token(token):
    """Extract server region from JWT token"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        lock_region = decoded.get("lock_region", "IND")
        return lock_region.upper()
    except:
        return "IND"

# -----------------------------
# Retry Decorator - 10 baar try karega
# -----------------------------
def retry_operation(max_retries=10, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if result and result.get('status') in ['success', 'failed']:
                        return result
                    # Agar result nahi aaya toh retry karo
                    print(f"Attempt {attempt + 1}/{max_retries} failed, retrying...")
                except Exception as e:
                    last_exception = e
                    print(f"Attempt {attempt + 1}/{max_retries} failed with error: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(delay)
            
            # Agar 10 baar mein bhi fail hua toh last error return karo
            if last_exception:
                return {
                    "status": "error",
                    "message": f"All {max_retries} attempts failed",
                    "error": str(last_exception)
                }
            return {
                "status": "error", 
                "message": f"All {max_retries} attempts failed"
            }
        return wrapper
    return decorator

# -----------------------------
# JWT Token Generation Functions - FIXED
# -----------------------------
def get_token_from_uid_password(uid, password):
    """Get JWT token using UID and password - FIXED VERSION"""
    try:
        oauth_url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        payload = {
            'uid': uid,
            'password': password,
            'response_type': "token",
            'client_type': "2",
            'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            'client_id': "100067"
        }
        
        headers = {
            'User-Agent': "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;pt;BR;)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip"
        }

        oauth_response = requests.post(oauth_url, data=payload, headers=headers, timeout=10, verify=False)
        oauth_response.raise_for_status()
        
        oauth_data = oauth_response.json()
        
        if 'access_token' not in oauth_data:
            return None, "OAuth response missing access_token"

        access_token = oauth_data['access_token']
        open_id = oauth_data.get('open_id', '')
        
        # Try platforms with the obtained credentials
        platforms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        
        for platform_type in platforms:
            result = try_platform_login(open_id, access_token, platform_type)
            if result and 'token' in result:
                return result['token'], None
        
        return None, "Login successful but JWT generation failed on all platforms"

    except requests.RequestException as e:
        return None, f"OAuth request failed: {str(e)}"
    except ValueError:
        return None, "Invalid JSON response from OAuth service"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def try_platform_login(open_id, access_token, platform_type):
    """Try login for a specific platform - IMPROVED VERSION"""
    try:
        game_data = my_pb2.GameData()
        game_data.timestamp = "2024-12-05 18:15:32"
        game_data.game_name = "free fire"
        game_data.game_version = 1
        game_data.version_code = "1.108.3"
        game_data.os_info = "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)"
        game_data.device_type = "Handheld"
        game_data.network_provider = "Verizon Wireless"
        game_data.connection_type = "WIFI"
        game_data.screen_width = 1280
        game_data.screen_height = 960
        game_data.dpi = "240"
        game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
        game_data.total_ram = 5951
        game_data.gpu_name = "Adreno (TM) 640"
        game_data.gpu_version = "OpenGL ES 3.0"
        game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
        game_data.ip_address = "172.190.111.97"
        game_data.language = "en"
        game_data.open_id = open_id
        game_data.access_token = access_token
        game_data.platform_type = platform_type
        game_data.field_99 = str(platform_type)
        game_data.field_100 = str(platform_type)

        serialized_data = game_data.SerializeToString()
        encrypted_data = encrypt_message(serialized_data)
        hex_encrypted_data = binascii.hexlify(encrypted_data).decode('utf-8')

        url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB51"
        }
        
        edata = bytes.fromhex(hex_encrypted_data)

        response = requests.post(url, data=edata, headers=headers, timeout=10, verify=False)
        response.raise_for_status()

        if response.status_code == 200:
            # Parse response
            data_dict = None
            try:
                example_msg = output_pb2.Garena_420()
                example_msg.ParseFromString(response.content)
                data_dict = {field.name: getattr(example_msg, field.name)
                             for field in example_msg.DESCRIPTOR.fields
                             if field.name not in ["binary", "binary_data", "Garena420"]}
            except Exception as e:
                try:
                    data_dict = response.json()
                except ValueError:
                    return None

            if data_dict and "token" in data_dict:
                token_value = data_dict["token"]
                try:
                    decoded_token = jwt.decode(token_value, options={"verify_signature": False})
                except Exception:
                    decoded_token = {}

                return {
                    "account_id": decoded_token.get("account_id"),
                    "account_name": decoded_token.get("nickname"),
                    "open_id": open_id,
                    "access_token": access_token,
                    "platform": decoded_token.get("external_type"),
                    "region": decoded_token.get("lock_region"),
                    "status": "success",
                    "token": token_value
                }
        
        return None

    except Exception:
        return None

# -----------------------------
# Player Info Functions
# -----------------------------
def create_info_protobuf(uid):
    message = uid_generator_pb2.uid_generator()
    message.saturn_ = int(uid)
    message.garena = 1
    return message.SerializeToString()

def get_player_info(target_uid, token, server_name=None):
    """Get detailed player information"""
    try:
        if not server_name:
            server_name = get_server_from_token(token)
            
        protobuf_data = create_info_protobuf(target_uid)
        encrypted_data = encrypt_message_hex(protobuf_data)
        endpoint = get_base_url(server_name) + "GetPlayerPersonalShow"

        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB51"
        }

        response = requests.post(endpoint, data=bytes.fromhex(encrypted_data), headers=headers, verify=False)
        
        if response.status_code != 200:
            return None

        hex_response = response.content.hex()
        binary = bytes.fromhex(hex_response)
        
        info = data_pb2.AccountPersonalShowInfo()
        info.ParseFromString(binary)
        
        return info
    except Exception as e:
        print(f"Error getting player info: {e}")
        return None

def extract_player_info(info_data):
    """Extract player information from protobuf response"""
    if not info_data:
        return None

    basic_info = info_data.basic_info
    return {
        'uid': basic_info.account_id,
        'nickname': basic_info.nickname,
        'level': basic_info.level,
        'region': basic_info.region,
        'likes': basic_info.liked,
        'release_version': basic_info.release_version
    }

# -----------------------------
# Authentication Helper Functions
# -----------------------------
def decode_author_uid(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("account_id") or decoded.get("sub")
    except:
        return None

# -----------------------------
# Friend Management Functions - WITH RETRY
# -----------------------------
@retry_operation(max_retries=10, delay=1)
def remove_friend_with_retry(author_uid, target_uid, token, server_name=None):
    """Remove friend with retry mechanism"""
    try:
        if not server_name:
            server_name = get_server_from_token(token)
            
        # Get player info
        player_info = get_player_info(target_uid, token, server_name)
        
        msg = RemoveFriend_Req_pb2.RemoveFriend()
        msg.AuthorUid = int(author_uid)
        msg.TargetUid = int(target_uid)
        encrypted_bytes = encrypt_message(msg.SerializeToString())

        url = get_base_url(server_name) + "RemoveFriend"
        headers = {
            'Authorization': f"Bearer {token}",
            'User-Agent': "Dalvik/2.1.0 (Linux; Android 9)",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB51"
        }

        res = requests.post(url, data=encrypted_bytes, headers=headers, verify=False)
        
        # Extract player info
        player_data = None
        if player_info:
            player_data = extract_player_info(player_info)
        
        # Check if successful
        if res.status_code == 200:
            status = "success"
        else:
            status = "failed"
            # Force retry by raising exception
            raise Exception(f"HTTP {res.status_code}: {res.text}")
        
        # Simplified response format
        response_data = {
            "author_uid": author_uid,
            "nickname": player_data.get('nickname') if player_data else "Unknown",
            "uid": target_uid,
            "level": player_data.get('level') if player_data else 0,
            "likes": player_data.get('likes') if player_data else 0,
            "region": player_data.get('region') if player_data else "Unknown",
            "release_version": player_data.get('release_version') if player_data else "Unknown",
            "status": status,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return response_data

    except Exception as e:
        print(f"Remove friend error: {e}")
        raise e  # Retry ke liye exception raise karo

@retry_operation(max_retries=10, delay=1)
def send_friend_request_with_retry(author_uid, target_uid, token, server_name=None):
    """Send friend request with retry mechanism"""
    try:
        if not server_name:
            server_name = get_server_from_token(token)
            
        # Get player info
        player_info = get_player_info(target_uid, token, server_name)
        
        encrypted_id = Encrypt_ID(target_uid)
        payload = f"08a7c4839f1e10{encrypted_id}1801"
        encrypted_payload = encrypt_api(payload)

        url = get_base_url(server_name) + "RequestAddingFriend"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB51",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)"
        }

        r = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload), verify=False)
        
        # Extract player info
        player_data = None
        if player_info:
            player_data = extract_player_info(player_info)
        
        # Check if successful
        if r.status_code == 200:
            status = "success"
        else:
            status = "failed"
            # Force retry by raising exception
            raise Exception(f"HTTP {r.status_code}: {r.text}")
        
        # Simplified response format
        response_data = {
            "author_uid": author_uid,
            "nickname": player_data.get('nickname') if player_data else "Unknown",
            "uid": target_uid,
            "level": player_data.get('level') if player_data else 0,
            "likes": player_data.get('likes') if player_data else 0,
            "region": player_data.get('region') if player_data else "Unknown",
            "release_version": player_data.get('release_version') if player_data else "Unknown",
            "status": status,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return response_data
        
    except Exception as e:
        print(f"Add friend error: {e}")
        raise e  # Retry ke liye exception raise karo

# -----------------------------
# API Routes - WITH RETRY
# -----------------------------
@app.route('/remove_friend', methods=['GET'])
def remove_friend_api():
    """Remove friend using either token or UID/password - WITH RETRY"""
    token = request.args.get('token')
    player_id = request.args.get('player_id')
    uid = request.args.get('uid')
    password = request.args.get('password')
    server_name = request.args.get('server_name')

    # Validate input
    if not player_id:
        return jsonify({
            "status": "failed",
            "message": "Missing 'player_id'"
        }), 400

    # Get token from either direct token or UID/password
    if token:
        # Use provided token directly
        author_uid = decode_author_uid(token)
        if not author_uid:
            return jsonify({
                "status": "failed", 
                "message": "Invalid token"
            }), 400
    elif uid and password:
        # Generate token from UID/password - FIXED
        print(f"Attempting to generate token for UID: {uid}")
        token, error = get_token_from_uid_password(uid, password)
        if error:
            print(f"Token generation failed: {error}")
            return jsonify({
                "status": "failed",
                "message": error
            }), 400
        print(f"Token generated successfully")
        author_uid = decode_author_uid(token)
        if not author_uid:
            return jsonify({
                "status": "failed", 
                "message": "Generated token is invalid"
            }), 400
    else:
        return jsonify({
            "status": "failed",
            "message": "Either 'token' or 'uid' and 'password' must be provided"
        }), 400

    # Retry mechanism ke saath remove friend call karo
    result = remove_friend_with_retry(author_uid, player_id, token, server_name)
    return jsonify(result)

@app.route('/add_friend', methods=['GET'])
def add_friend_api():
    """Add friend using either token or UID/password - WITH RETRY"""
    token = request.args.get('token')
    player_id = request.args.get('player_id')
    uid = request.args.get('uid')
    password = request.args.get('password')
    server_name = request.args.get('server_name')

    # Validate input
    if not player_id:
        return jsonify({
            "status": "failed",
            "message": "Missing 'player_id'"
        }), 400

    # Get token from either direct token or UID/password
    if token:
        # Use provided token directly
        author_uid = decode_author_uid(token)
        if not author_uid:
            return jsonify({
                "status": "failed", 
                "message": "Invalid token"
            }), 400
    elif uid and password:
        # Generate token from UID/password
        token, error = get_token_from_uid_password(uid, password)
        if error:
            return jsonify({
                "status": "failed",
                "message": error
            }), 400
        author_uid = decode_author_uid(token)
    else:
        return jsonify({
            "status": "failed",
            "message": "Either 'token' or 'uid' and 'password' must be provided"
        }), 400

    # Retry mechanism ke saath add friend call karo
    result = send_friend_request_with_retry(author_uid, player_id, token, server_name)
    return jsonify(result)

@app.route('/get_player_info', methods=['GET'])
def get_player_info_api():
    """Get player information using either token or UID/password"""
    token = request.args.get('token')
    player_id = request.args.get('player_id')
    uid = request.args.get('uid')
    password = request.args.get('password')
    server_name = request.args.get('server_name')

    if not player_id:
        return jsonify({"status": "failed", "message": "Missing 'player_id'"}), 400

    # Get token from either direct token or UID/password
    if not token and uid and password:
        token, error = get_token_from_uid_password(uid, password)
        if error:
            return jsonify({"status": "failed", "message": error}), 400

    if not token:
        return jsonify({"status": "failed", "message": "Token required"}), 400

    player_info = get_player_info(player_id, token, server_name)
    if not player_info:
        return jsonify({"status": "failed", "message": "Failed to get player info"}), 400

    player_data = extract_player_info(player_info)
    if not player_data:
        return jsonify({"status": "failed", "message": "Failed to extract player info"}), 400

    # Add timestamp and format response
    player_data.update({
        "status": "success",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify(player_data)

# -----------------------------
# JWT Generation Routes (Optional)
# -----------------------------
@app.route('/token', methods=['GET'])
def oauth_guest():
    """Get token using UID and password - FIXED"""
    uid = request.args.get('uid')
    password = request.args.get('password')
    
    if not uid or not password:
        return jsonify({"message": "Missing uid or password"}), 400

    token, error = get_token_from_uid_password(uid, password)
    if error:
        return jsonify({"message": error}), 400
        
    # Verify the token is valid
    author_uid = decode_author_uid(token)
    if not author_uid:
        return jsonify({"message": "Generated token is invalid"}), 400
        
    return jsonify({
        "status": "success",
        "token": token,
        "uid": uid,
        "author_uid": author_uid
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "FreeFire-API"}), 200

# -----------------------------
# Run Server
# ----------------------------
# === Startup ===
import sys

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting {__name__.upper()} on port {port} ...")
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    app.run(host='0.0.0.0', port=port, debug=False)
