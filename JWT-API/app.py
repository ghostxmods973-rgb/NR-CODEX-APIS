from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import requests
import my_pb2
import output_pb2
import jwt
import asyncio

app = Flask(__name__)

AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

def encrypt_message(plaintext):
    """Encrypt message using AES CBC mode"""
    try:
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        padded_message = pad(plaintext, AES.block_size)
        return cipher.encrypt(padded_message)
    except Exception as e:
        raise Exception(f"Encryption failed: {str(e)}")

def fetch_open_id(access_token):
    """Fetch open_id using access token"""
    try:
        # First request to get UID
        uid_url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        uid_headers = {
            "authority": "prod-api.reward.ff.garena.com",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": access_token,
            "origin": "https://reward.ff.garena.com",
            "referer": "https://reward.ff.garena.com/",
            "sec-ch-ua": '"Not.A/Brand";v="99", "Chromium";v="124"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        uid_res = requests.get(uid_url, headers=uid_headers, timeout=10)
        uid_res.raise_for_status()
        uid_data = uid_res.json()
        uid = uid_data.get("uid")

        if not uid:
            return None, "Failed to extract UID from access token"

        # Second request to get open_id
        openid_url = "https://shop2game.com/api/auth/player_id_login"
        openid_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ar-MA,ar;q=0.9,en-US;q=0.8,en;q=0.7,ar-AE;q=0.6,fr-FR;q=0.5,fr;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://shop2game.com",
            "Referer": "https://shop2game.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"'
        }
        
        payload = {
            "app_id": 100067,
            "login_id": str(uid)
        }

        openid_res = requests.post(openid_url, headers=openid_headers, json=payload, timeout=10)
        openid_res.raise_for_status()
        openid_data = openid_res.json()
        open_id = openid_data.get("open_id")

        if not open_id:
            return None, "Failed to extract open_id from UID"

        return open_id, None

    except requests.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def try_platform_login(open_id, access_token, platform_type):
    """Try login for a specific platform"""
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
            "ReleaseVersion": "OB50"
        }
        
        edata = bytes.fromhex(hex_encrypted_data)

        response = requests.post(url, data=edata, headers=headers, timeout=10)
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
            except Exception:
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

@app.route('/access-jwt', methods=['GET'])
def majorlogin_jwt():
    """Generate JWT token using access token"""
    access_token = request.args.get('access_token')
    provided_open_id = request.args.get('open_id')

    if not access_token:
        return jsonify({"message": "missing access_token"}), 400

    open_id = provided_open_id
    if not open_id:
        open_id, error = fetch_open_id(access_token)
        if error:
            return jsonify({"message": error}), 400

    # Try different platforms
    platforms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    for platform_type in platforms:
        result = try_platform_login(open_id, access_token, platform_type)
        if result:
            return jsonify(result), 200

    return jsonify({"message": "No valid platform found for login"}), 400

@app.route('/token', methods=['GET'])
def oauth_guest():
    """Get token using UID and password"""
    uid = request.args.get('uid')
    password = request.args.get('password')
    
    if not uid or not password:
        return jsonify({"message": "Missing uid or password"}), 400

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

    try:
        oauth_response = requests.post(oauth_url, data=payload, headers=headers, timeout=10)
        oauth_response.raise_for_status()
        
        oauth_data = oauth_response.json()
        
        if 'access_token' not in oauth_data or 'open_id' not in oauth_data:
            return jsonify({"message": "OAuth response missing access_token or open_id"}), 500

        # Use the obtained access_token and open_id to generate JWT
        access_token = oauth_data['access_token']
        open_id = oauth_data['open_id']
        
        # Try platforms with the obtained credentials
        platforms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        
        for platform_type in platforms:
            result = try_platform_login(open_id, access_token, platform_type)
            if result:
                return jsonify(result), 200
        
        return jsonify({"message": "Login successful but JWT generation failed"}), 400

    except requests.RequestException as e:
        return jsonify({"message": f"OAuth request failed: {str(e)}"}), 500
    except ValueError:
        return jsonify({"message": "Invalid JSON response from OAuth service"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "JWT-API"}), 200

async def startup():
    """Startup tasks"""
    print("[✓] Service initialized successfully")

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting JWT-API on port {port} ...")
    
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    
    app.run(host='0.0.0.0', port=port, debug=False)
