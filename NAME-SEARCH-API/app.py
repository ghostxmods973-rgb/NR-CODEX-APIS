from flask import Flask, request, jsonify
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from freefire_pb2 import Players  # Make sure this is compiled from your .proto

app = Flask(__name__)

# ---------------------------------------------
# AES Key & IV
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ---------------------------------------------
# Region-based account credentials
def get_account_credentials(region: str) -> str:
    r = region.upper()
    if r == "IND":
        return "uid=4143483801&password=B5E51D2321C1EF1DE0B6F8C2EBA54380DDDC7A86E089EF8C7D8CF9BC1C47E10E"
    elif r in {"BR", "US", "SAC", "NA"}:
        return "uid=3943479585&password=096B73E96BE40391C9919DB663DC5E761F9022CB27136437BE508EAAC21BDD5C"
    else:
        return "uid=3943485048&password=98AC489CFAE0318159D0FE381A596415CB67E5C193F6AE1E1E394ED2B1E7061B"

# ---------------------------------------------
# Get JWT token
def get_jwt_token(region: str) -> str:
    creds = get_account_credentials(region)
    jwt_url = f"https://token-generator-e8xv.vercel.app/token?{creds}"
    try:
        res = requests.get(jwt_url)
        if res.status_code == 200:
            return res.json().get("token")
    except Exception as e:
        print(f"[JWT ERROR] {e}")
    return None

# ---------------------------------------------
# Encrypt nickname with AES
def encrypt_name(nickname: str) -> str:
    encoded = nickname.encode("utf-8")
    proto_hex = "0a" + format(len(encoded), '02x') + encoded.hex()
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(bytes.fromhex(proto_hex), AES.block_size))
    return encrypted.hex()

# ---------------------------------------------
# Get correct Free Fire server by region
def get_ff_server_url(region: str) -> str:
    region = region.upper()
    if region == "IND":
        return "https://client.ind.freefiremobile.com/FuzzySearchAccountByName"
    elif region in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/FuzzySearchAccountByName"
    else:
        return "https://clientbp.ggblueshark.com/FuzzySearchAccountByName"

# ---------------------------------------------
# Flask route for searching nickname
@app.route('/search', methods=['GET'])
def search():
    nickname = request.args.get("nickname")
    region = request.args.get("region", "")

    # Validate input
    if not nickname or not region:
        missing = []
        if not nickname:
            missing.append("nickname")
        if not region:
            missing.append("region")
        return jsonify({"error": f"Missing {', '.join(missing)}"}), 400

    # Get JWT token
    jwt_token = get_jwt_token(region)
    if not jwt_token:
        return jsonify({"error": "JWT token generation failed"}), 500

    # Encrypt nickname
    encrypted_data = encrypt_name(nickname)
    server_url = get_ff_server_url(region)

    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB51',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': f'Bearer {jwt_token}',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': server_url.split("//")[1].split("/")[0],
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    # Send request to Free Fire server
    try:
        response = requests.post(server_url, headers=headers, data=bytes.fromhex(encrypted_data), verify=False)

        if response.status_code == 200 and response.content:
            players = Players()
            players.ParseFromString(response.content)

            result = []
            for p in players.player:
                result.append({
                    "accountId": str(p.accountId),
                    "nickname": p.nickname,
                    "region": p.region,
                    "level": p.level,
                    "lastLogin": p.lastLogin
                })

            return jsonify({"players": result})
        else:
            return jsonify({"error": "No players found or request failed"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)