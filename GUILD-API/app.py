import httpx
import time
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from datetime import datetime
import asyncio
import data_pb2
import encode_id_clan_pb2

# ===================== CONFIG =====================
app = Flask(__name__)
freefire_version = "OB51"
key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
jwt_tokens = {}  # Store tokens by region (REG -> token string)
jwt_lock = threading.Lock()
# =================================================

# ===================== REGION CONFIG =====================
def get_region_credentials(region):
    r = region.upper()
    if r == "IND":
        return "uid=4218389302&password=NILAY-9LRRJQ7P3-NR-CODEX"
    elif r == "BD":
        return "uid=4218400521&password=BY_XRSUPER-JZRQ3RURQ-XRRRR"
    elif r in {"BR", "US", "SAC", "NA"}:
        return "uid=4218400521&password=BY_XRSUPER-JZRQ3RURQ-XRRRR"
    else:
        return "uid=4218400521&password=BY_XRSUPER-JZRQ3RURQ-XRRRR"

def parse_credentials(creds_str):
    """
    Parse strings like 'uid=123&password=ABC' -> (uid,password)
    Returns (None,None) if parsing fails.
    """
    try:
        parts = dict(pair.split("=", 1) for pair in creds_str.split("&"))
        return parts.get("uid"), parts.get("password")
    except Exception:
        return None, None

# ===================== ENCRYPT UID =====================
def Encrypt_ID(x):
    x = int(x)
    dec = [f'{i:02x}' for i in range(128, 256)]
    xxx = [f'{i:02x}' for i in range(0, 128)]

    parts = []
    while x > 0:
        parts.append(x % 128)
        x //= 128
    while len(parts) < 5:
        parts.append(0)
    parts.reverse()

    return ''.join(dec[parts[i]] if i > 0 else xxx[parts[i]] for i in range(5))

# ===================== AES ENCRYPT =====================
def encrypt_api(plain_text_hex):
    plain_text = bytes.fromhex(plain_text_hex)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plain_text, 16)).hex()

# ===================== EMOTE ID EN/DE =====================
def Encrypt_id_emote(uid):
    result = []
    while uid > 0:
        byte = uid & 0x7F
        uid >>= 7
        if uid > 0:
            byte |= 0x80
        result.append(byte)
    return bytes(result).hex()

def Decrypt_id_emote(uidd):
    bytes_value = bytes.fromhex(uidd)
    r, shift = 0, 0
    for byte in bytes_value:
        r |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return r

# ===================== TIMESTAMP =====================
def convert_timestamp(ts):
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

# ===================== JWT TOKEN (from freefireservice oauth) =====================
# We'll use the credentials (uid,password) to build the `data` param like: uid:password
# and hit: https://api.freefireservice.dnc.su/oauth/account:login?data={uid:password}
# The remote response may contain a JWT somewhere; we'll regex-search for a string that starts with 'ey' (typical JWT).
JWT_REGEX = re.compile(r'(eyJ[A-Za-z0-9_\-\.=]+)')

async def get_jwt_token(region):
    global jwt_tokens
    creds = get_region_credentials(region)
    uid, password = parse_credentials(creds)
    if not uid or not password:
        print(f"[-] Bad credentials for {region}: {creds}")
        return False

    # Build the login URL using uid:password as the data parameter (as you showed)
    data_param = f"{uid}:{password}"
    url = f"https://api.freefireservice.dnc.su/oauth/account:login?data={data_param}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            text = resp.text or ""
            # Try JSON parse first (some endpoints return JSON with token fields)
            token_candidate = None
            try:
                j = resp.json()
                # Common keys to check
                for k in ("token", "jwt", "access_token", "data", "auth"):
                    v = j.get(k)
                    if isinstance(v, str) and v.startswith("ey"):
                        token_candidate = v
                        break
                # sometimes token is nested inside data or result
                if not token_candidate:
                    # flatten and search for any string starting with ey
                    def find_ey(obj):
                        if isinstance(obj, str) and obj.startswith("ey"):
                            return obj
                        if isinstance(obj, dict):
                            for vv in obj.values():
                                res = find_ey(vv)
                                if res:
                                    return res
                        if isinstance(obj, list):
                            for item in obj:
                                res = find_ey(item)
                                if res:
                                    return res
                        return None
                    token_candidate = find_ey(j)
            except Exception:
                token_candidate = None

            # fallback to regex search in raw text
            if not token_candidate:
                m = JWT_REGEX.search(text)
                if m:
                    token_candidate = m.group(1)

            # Final fallback: maybe an HTTP header contains token
            if not token_candidate:
                # search all header values
                for hv in resp.headers.values():
                    m = JWT_REGEX.search(hv)
                    if m:
                        token_candidate = m.group(1)
                        break

            if token_candidate:
                with jwt_lock:
                    jwt_tokens[region.upper()] = token_candidate
                print(f"[+] JWT Token Updated for {region}: {token_candidate[:50]}...")
                return True
            else:
                print(f"[-] No JWT-like token found in response for {region}. HTTP {resp.status_code}.")
                # store empty to indicate attempt (so /health can show not-ready)
                with jwt_lock:
                    jwt_tokens[region.upper()] = ""
                return False
    except Exception as e:
        print(f"[-] JWT Token Error for {region}: {e}")
        return False

async def token_updater():
    regions = ["IND", "BD", "BR", "US", "SAC", "NA"]
    # initial quick run
    while True:
        for region in regions:
            try:
                await get_jwt_token(region)
                await asyncio.sleep(1)  # small throttle between region calls
            except Exception as e:
                print(f"token_updater error for {region}: {e}")
        # Sleep 8 hours between full refreshes (converted to seconds)
        await asyncio.sleep(8 * 3600)

# ===================== RUNNER: background asyncio loop in separate thread =====================
def _run_asyncio_token_updater_in_thread():
    # This runs in a separate thread to avoid interfering with Flask's main thread
    try:
        asyncio.run(token_updater())
    except Exception as e:
        print(f"Background token updater exited: {e}")

def start_token_updater_thread():
    t = threading.Thread(target=_run_asyncio_token_updater_in_thread, daemon=True)
    t.start()
    print("[*] Token updater thread started (daemon).")

# ===================== CLAN INFO ROUTE (SYNC) =====================
@app.route('/info', methods=['GET'])
def get_clan_info():
    clan_id = request.args.get('clan_id')
    region = request.args.get('region', 'IND').upper()

    if not clan_id:
        return jsonify({"error": "clan_id is required"}), 400

    with jwt_lock:
        token = jwt_tokens.get(region)

    if not token:
        return jsonify({"error": f"JWT token for region {region} not ready. Try again in a few seconds."}), 503

    try:
        # Prepare Protobuf
        # Build the same structure you had: {"1": int(clan_id), "2": 1}
        json_data = json.dumps({"1": int(clan_id), "2": 1})
        my_data = encode_id_clan_pb2.MyData()
        json_obj = json.loads(json_data)
        my_data.field1 = json_obj["1"]
        my_data.field2 = json_obj["2"]

        data_bytes = my_data.SerializeToString()
        # Use AES/CBC with your key/iv and PKCS7 pad
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data_bytes, 16))

        # Determine API endpoint based on region
        if region == "IND":
            url = "https://client.ind.freefiremobile.com/GetClanInfoByClanID"
            host = "client.ind.freefiremobile.com"
        elif region == "BD":
            url = "https://client.bd.freefiremobile.com/GetClanInfoByClanID"
            host = "client.bd.freefiremobile.com"
        elif region in ["BR", "SAC"]:
            url = "https://client.br.freefiremobile.com/GetClanInfoByClanID"
            host = "client.br.freefiremobile.com"
        elif region in ["US", "NA"]:
            url = "https://client.na.freefiremobile.com/GetClanInfoByClanID"
            host = "client.na.freefiremobile.com"
        else:
            url = "https://client.ind.freefiremobile.com/GetClanInfoByClanID"
            host = "client.ind.freefiremobile.com"

        # Request headers
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": freefire_version,
            "Content-Type": "application/octet-stream",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
            "Host": host,
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }

        # Synchronous HTTP using httpx
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, content=encrypted_data)

        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}", "body": response.text[:200]}), 500

        # Decrypt & Parse Response
        # NOTE: You previously called resp.ParseFromString(response.content)
        # If the remote response is encrypted, you'd need to decrypt here. This code assumes
        # server returned protobuf raw bytes directly (same as your original code).
        resp = data_pb2.response()
        resp.ParseFromString(response.content)

        def ts(x): 
            try:
                return datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return None

        result = {
            "id": getattr(resp, "id", None),
            "clan_name": getattr(resp, "special_code", None),
            "created_at": ts(getattr(resp, "timestamp1", 0)),
            "updated_at": ts(getattr(resp, "timestamp2", 0)),
            "last_active": ts(getattr(resp, "last_active", 0)),
            "level": getattr(resp, "level", None),
            "region": getattr(resp, "region", None),
            "welcome_message": getattr(resp, "welcome_message", None),
            "score": getattr(resp, "score", None),
            "xp": getattr(resp, "xp", None),
            "rank": getattr(resp, "rank", None),
            "members_online": getattr(getattr(resp, "guild_details", None), "members_online", None),
            "total_members": getattr(getattr(resp, "guild_details", None), "total_members", None),
            "clan_id": getattr(getattr(resp, "guild_details", None), "clan_id", None),
            "error_code": getattr(resp, "error_code", None),
            "status": "success",
            "requested_region": region
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

# ===================== HEALTH CHECK =====================
@app.route('/health', methods=['GET'])
def health_check():
    regions_status = {}
    for region in ["IND", "BD", "BR", "US", "SAC", "NA"]:
        with jwt_lock:
            token = jwt_tokens.get(region)
        regions_status[region] = "ready" if token and token.startswith("ey") else "not ready"
    
    return jsonify({
        "status": "running",
        "regions": regions_status,
        "timestamp": datetime.now().isoformat()
    })

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
