
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests
import json
import base64
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

app = Flask(__name__)

# --- Encryption setup ---
key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
freefire_version = "OB51"

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

def get_bio_server_url(lock_region: str):
    """Region ke hisaab se Free Fire bio endpoint select kare"""
    region = lock_region.upper()
    if region == "IND":
        return "https://client.ind.freefiremobile.com/UpdateSocialBasicInfo"
    elif region in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/UpdateSocialBasicInfo"
    elif region == "BD":
        return "https://client.bd.freefiremobile.com/UpdateSocialBasicInfo"
    elif region == "SG":
        return "https://client.sg.freefiremobile.com/UpdateSocialBasicInfo"
    else:
        return "https://clientbp.ggblueshark.com/UpdateSocialBasicInfo"

@app.route('/set-bio', methods=['GET'])
def set_bio():
    jwt_token = request.args.get('token')
    bio_text = request.args.get('bio')
    
    if not jwt_token or not bio_text:
        return jsonify({
            "status": "error",
            "message": "Missing token or bio parameter"
        }), 400

    # --- JWT decode karke lock_region nikalna ---
    payload = decode_jwt_noverify(jwt_token)
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Invalid JWT token"
        }), 400

    lock_region = payload.get("lock_region", "IND").upper()
    url_bio = get_bio_server_url(lock_region)

    # --- Protobuf setup ---
    _sym_db = _symbol_database.Default()
    DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\ndata.proto\"\xbb\x01\n\x04\x44\x61ta\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05\x12\x1e\n\x07\x66ield_5\x18\x05 \x01(\x0b\x32\r.EmptyMessage\x12\x1e\n\x07\x66ield_6\x18\x06 \x01(\x0b\x32\r.EmptyMessage\x12\x0f\n\x07\x66ield_8\x18\x08 \x01(\t\x12\x0f\n\x07\x66ield_9\x18\t \x01(\x05\x12\x1f\n\x08\x66ield_11\x18\x0b \x01(\x0b\x32\r.EmptyMessage\x12\x1f\n\x08\x66ield_12\x18\x0c \x01(\x0b\x32\r.EmptyMessage\"\x0e\n\x0c\x45mptyMessageb\x06proto3')
    _globals = globals()
    _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
    _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'data1_pb2', _globals)
    
    if _descriptor._USE_C_DESCRIPTORS == False:
        DESCRIPTOR._options = None
        _globals['_DATA']._serialized_start = 15
        _globals['_DATA']._serialized_end = 202
        _globals['_EMPTYMESSAGE']._serialized_start = 204
        _globals['_EMPTYMESSAGE']._serialized_end = 218
    
    Data = _sym_db.GetSymbol('Data')
    EmptyMessage = _sym_db.GetSymbol('EmptyMessage')
    
    # Build protobuf message
    data = Data()
    data.field_2 = 17
    data.field_5.CopyFrom(EmptyMessage())
    data.field_6.CopyFrom(EmptyMessage())
    data.field_8 = bio_text
    data.field_9 = 1
    data.field_11.CopyFrom(EmptyMessage())
    data.field_12.CopyFrom(EmptyMessage())
    
    # Encrypt protobuf
    data_bytes = data.SerializeToString()
    padded_data = pad(data_bytes, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(padded_data)
    
    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": freefire_version,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    
    try:
        res_bio = requests.post(url_bio, headers=headers, data=encrypted_data, timeout=10)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"External request failed: {str(e)}"
        }), 500

    if res_bio.status_code == 200:
        return jsonify({
            "status": "success",
            "message": "Bio updated successfully",
            "lock_region": lock_region,
            "bio_text": bio_text
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"External server returned status {res_bio.status_code}",
            "lock_region": lock_region,
            "external_response": res_bio.text
        }), 400

import sys

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting {__name__.upper()} on port {port} ...")
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    app.run(host='0.0.0.0', port=port, debug=False)
