from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests
import time
import json
import base64

app = Flask(__name__)

# --- Protobuf setup ---
from google.protobuf import message_factory
from google.protobuf import descriptor_pool

pool = descriptor_pool.Default()
fd = pool.AddSerializedFile(b'\n\ndata.proto"7\n\x12InnerNestedMessage\x12\x0f\n\x07\x66ield_6\x18\x06 \x01(\x03\x12\x10\n\x08\x66ield_14\x18\x0e \x01(\x03"\x87\x01\n\nNestedItem\x12\x0f\n\x07\x66ield_1\x18\x01 \x01(\x05\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05\x12\x0f\n\x07\x66ield_3\x18\x03 \x01(\x05\x12\x0f\n\x07\x66ield_4\x18\x04 \x01(\x05\x12\x0f\n\x07\x66ield_5\x18\x05 \x01(\x05\x12$\n\x07\x66ield_6\x18\x06 \x01(\x0b\x32\x13.InnerNestedMessage"@\n\x0fNestedContainer\x12\x0f\n\x07\x66ield_1\x18\x01 \x01(\x05\x12\x1c\n\x07\x66ield_2\x18\x02 \x03(\x0b\x32\x0b.NestedItem"A\n\x0bMainMessage\x12\x0f\n\x07\x66ield_1\x18\x01 \x01(\x05\x12!\n\x07\x66ield_2\x18\x02 \x03(\x0b\x32\x10.NestedContainerb\x06proto3')

MainMessage = message_factory.GetMessageClass(pool.FindMessageTypeByName('MainMessage'))
NestedContainer = message_factory.GetMessageClass(pool.FindMessageTypeByName('NestedContainer'))
NestedItem = message_factory.GetMessageClass(pool.FindMessageTypeByName('NestedItem'))
InnerNestedMessage = message_factory.GetMessageClass(pool.FindMessageTypeByName('InnerNestedMessage'))

# --- Encryption setup ---
key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
freefire_version = "OB50"

def decode_jwt_noverify(token: str):
    """JWT ko bina verify kiye payload decode karta hai"""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)  # padding fix
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        return payload
    except Exception:
        return None

def get_server_url(lock_region: str):
    """Region ke hisaab se Free Fire endpoint select kare"""
    region = lock_region.upper()
    
    # Region to URL mapping
    region_map = {
        "IND": "https://client.ind.freefiremobile.com/SetPlayerGalleryShowInfo",
        "BR": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo", 
        "US": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo",
        "SAC": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo",
        "NA": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo",
        "BD": "https://client.bd.freefiremobile.com/SetPlayerGalleryShowInfo",
        "SG": "https://client.sg.freefiremobile.com/SetPlayerGalleryShowInfo",
        "ME": "https://client.me.freefiremobile.com/SetPlayerGalleryShowInfo",
        "PK": "https://client.pk.freefiremobile.com/SetPlayerGalleryShowInfo",
        "EU": "https://client.eu.freefiremobile.com/SetPlayerGalleryShowInfo",
        "ID": "https://client.id.freefiremobile.com/SetPlayerGalleryShowInfo",
        "VN": "https://client.vn.freefiremobile.com/SetPlayerGalleryShowInfo",
        "TH": "https://client.th.freefiremobile.com/SetPlayerGalleryShowInfo",
        "PH": "https://client.ph.freefiremobile.com/SetPlayerGalleryShowInfo",
        "MY": "https://client.my.freefiremobile.com/SetPlayerGalleryShowInfo",
        "TR": "https://client.tr.freefiremobile.com/SetPlayerGalleryShowInfo"
    }
    
    # Agar region mapping mein hai to woh URL use karo
    if region in region_map:
        return region_map[region]
    else:
        # Default URL for all other regions
        return "https://clientbp.ggblueshark.com/SetPlayerGalleryShowInfo"

@app.route('/add-profile', methods=['GET'])
def add_profile():
    jwt_token = request.args.get('token')
    itemid_str = request.args.get('itemid')
    
    if not jwt_token or not itemid_str:
        return jsonify({
            "status": False,
            "message": "Missing token or itemid parameter"
        }), 400

    # --- JWT decode karke lock_region nikalna ---
    payload = decode_jwt_noverify(jwt_token)
    if not payload:
        return jsonify({
            "status": False,
            "message": "Invalid JWT token"
        }), 400

    lock_region = payload.get("lock_region", "IND").upper()  # agar missing hai to default IND
    url = get_server_url(lock_region)

    # --- Process item IDs ---
    item_ids = itemid_str.split('/')[:15]
    if not item_ids:
        return jsonify({"status": False, "message": "At least one item ID required"}), 400

    # Build protobuf message using the structure from old code
    data = MainMessage()
    data.field_1 = 1
    
    container1 = data.field_2.add()
    container1.field_1 = 1
    
    # Item combinations from old code
    items = [
        {"field_1": 2, "field_4": 1},
        {"field_1": 2, "field_4": 1, "field_5": 4},
        {"field_1": 2, "field_4": 1, "field_5": 2},
        {"field_1": 13, "field_3": 1},
        {"field_1": 13, "field_3": 1, "field_4": 2},
        {"field_1": 13, "field_3": 1, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_5": 4},
        {"field_1": 13, "field_3": 1, "field_4": 2, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_4": 2, "field_5": 4},
        {"field_1": 13, "field_3": 1, "field_4": 4},
        {"field_1": 13, "field_3": 1, "field_4": 4, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_4": 4, "field_5": 4},
        {"field_1": 13, "field_3": 1, "field_4": 6},
        {"field_1": 13, "field_3": 1, "field_4": 6, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_4": 6, "field_5": 4}
    ]
    
    for i, item_id in enumerate(item_ids):
        if i >= len(items):
            break
        item_data = items[i]
        item = container1.field_2.add()
        item.field_1 = item_data.get("field_1", 0)
        if "field_3" in item_data:
            item.field_3 = item_data["field_3"]
        if "field_4" in item_data:
            item.field_4 = item_data["field_4"]
        if "field_5" in item_data:
            item.field_5 = item_data["field_5"]
        inner = InnerNestedMessage()
        inner.field_6 = int(item_id)
        item.field_6.CopyFrom(inner)

    # Additional container from old code
    container2 = data.field_2.add()
    container2.field_1 = 9
    
    item7 = container2.field_2.add()
    item7.field_4 = 3
    inner7 = InnerNestedMessage()
    inner7.field_14 = 3048205855
    item7.field_6.CopyFrom(inner7)
    
    item8 = container2.field_2.add()
    item8.field_4 = 3
    item8.field_5 = 3
    inner8 = InnerNestedMessage()
    inner8.field_14 = 3048205855
    item8.field_6.CopyFrom(inner8)

    # --- Encrypt protobuf ---
    data_bytes = data.SerializeToString()
    padded_data = pad(data_bytes, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(padded_data)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": freefire_version,
        "Content-Type": "application/octet-stream",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Accept-Encoding": "gzip"
    }

    try:
        response = requests.post(url, headers=headers, data=encrypted_data, timeout=10)
    except Exception as e:
        return jsonify({
            "status": False,
            "message": f"External request failed: {str(e)}"
        }), 500

    current_time = int(time.time())
    add_profile_list = [{"add_time": current_time, f"item_id{i+1}": int(item_id)} 
                        for i, item_id in enumerate(item_ids)]

    if response.status_code == 200:
        return jsonify({
            "message": "Item added to profile",
            "status": True,
            "lock_region": lock_region,
            "server_used": url,
            "Add-profile": add_profile_list,
            "response_code": response.status_code
        })
    else:
        return jsonify({
            "status": False,
            "message": f"External server returned status {response.status_code}",
            "lock_region": lock_region,
            "server_used": url,
            "external_response": response.text,
            "request_size": len(encrypted_data),
            "response_code": response.status_code
        }), 400

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": True,
        "message": "API is running successfully",
        "version": "1.0",
        "freefire_version": freefire_version
    })

@app.route('/regions', methods=['GET'])
def get_regions():
    """Get all supported regions"""
    regions = {
        "IND": "India",
        "BR": "Brazil", 
        "US": "United States",
        "SAC": "South America",
        "NA": "North America",
        "BD": "Bangladesh",
        "SG": "Singapore",
        "ME": "Middle East",
        "PK": "Pakistan",
        "EU": "Europe",
        "ID": "Indonesia",
        "VN": "Vietnam",
        "TH": "Thailand",
        "PH": "Philippines",
        "MY": "Malaysia",
        "TR": "Turkey",
        "DEFAULT": "Other Regions"
    }
    return jsonify({
        "status": True,
        "regions": regions
    })

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Free Fire Profile API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f0f2f5; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .endpoint { background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #007bff; }
                code { background: #e9ecef; padding: 3px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
                .success { color: #28a745; }
                .error { color: #dc3545; }
                .info { color: #17a2b8; }
                h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Free Fire Profile API</h1>
                <p><strong>Yeh API Free Fire mein items ko profile mein add karne ke liye hai.</strong></p>
                
                <div class="endpoint">
                    <h3>📡 API Endpoint: <code>GET /add-profile</code></h3>
                    <p><strong>Parameters:</strong></p>
                    <ul>
                        <li><code>token</code> - JWT token (required)</li>
                        <li><code>itemid</code> - Item IDs separated by / (max 15 items)</li>
                    </ul>
                    
                    <p><strong>Example Request:</strong></p>
                    <code>http://your-server.com:5000/add-profile?token=your_jwt_token&itemid=12345/67890/54321</code>
                    
                    <p><strong>Success Response:</strong></p>
                    <pre>
{
    "status": true,
    "message": "Item added to profile",
    "lock_region": "IND",
    "server_used": "https://client.ind.freefiremobile.com/SetPlayerGalleryShowInfo",
    "Add-profile": [
        {"add_time": 1700000000, "item_id1": 12345},
        {"add_time": 1700000000, "item_id2": 67890}
    ]
}
                    </pre>
                    
                    <p><strong>Error Response:</strong></p>
                    <pre>
{
    "status": false,
    "message": "Error description"
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>🌍 Supported Regions</h3>
                    <ul>
                        <li><strong>IND</strong> - India</li>
                        <li><strong>BR, US, SAC, NA</strong> - Americas</li>
                        <li><strong>BD</strong> - Bangladesh</li>
                        <li><strong>SG</strong> - Singapore</li>
                        <li><strong>ME, PK, TR</strong> - Middle East</li>
                        <li><strong>EU</strong> - Europe</li>
                        <li><strong>ID, VN, TH, PH, MY</strong> - Southeast Asia</li>
                        <li><strong>Others</strong> - Default server</li>
                    </ul>
                </div>
                
                <div class="endpoint">
                    <h3>🔧 Additional Endpoints</h3>
                    <p><code>GET /health</code> - API health check</p>
                    <p><code>GET /regions</code> - List all supported regions</p>
                </div>
                
                <div class="endpoint">
                    <h3>📊 Status Codes</h3>
                    <p><span class="success">✓ status: true</span> - Operation successful</p>
                    <p><span class="error">✗ status: false</span> - Operation failed</p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #666;">
                <p>NR_CODEX</p>
            </div>
        </body>
    </html>
    """

import sys

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting {__name__.upper()} on port {port} ...")
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    app.run(host='0.0.0.0', port=port, debug=False)