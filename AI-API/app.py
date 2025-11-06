from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

SAMBA_API_KEY = "628081f7-96e9-4bf1-a467-488a2f33284c"
SAMBA_URL = "https://api.sambanova.ai/v1/chat/completions"

@app.route("/ask", methods=["GET"])
def ask_sambanova():
    message = request.args.get("message")
    key = request.args.get("Key")
    
    if key != "NR-CODEX":
        return jsonify({"error": "Invalid API Key!"}), 401

    if not message:
        return jsonify({"error": "Missing message parameter!"}), 400
        
    headers = {
        "Authorization": f"Bearer {SAMBA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "ALLaM-7B-Instruct-preview",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": message}
        ],
        "temperature": 0.1,
        "top_p": 0.1
    }

    try:
        response = requests.post(SAMBA_URL, headers=headers, json=payload, timeout=30)
        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            reply = data["choices"][0]["message"]["content"]
        else:
            reply = "No response from model."

        return jsonify({
            "status": "success",
            "message": message,
            "reply": reply
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting AI-API on port {port} ...")
    
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"Startup warning: {e} — continuing without full initialization")
    
    app.run(host='0.0.0.0', port=port, debug=False)
