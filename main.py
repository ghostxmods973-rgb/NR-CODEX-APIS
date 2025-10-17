import os
import subprocess
import threading
import time
import socket
import requests
from flask import Flask, request, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
running_apps = {}
START_PORT = 9000  # internal sub-apps ports

# -----------------------------
# Utility functions
# -----------------------------
def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0

def install_requirements(folder):
    req_file = os.path.join(BASE_DIR, folder, "requirements.txt")
    if os.path.exists(req_file):
        print(f"[📦] Installing requirements for {folder}...")
        subprocess.run(["pip3", "install", "-r", req_file])

def start_app(folder, port):
    app_path = os.path.join(BASE_DIR, folder, "app.py")
    if not os.path.exists(app_path):
        print(f"[❌] {folder}/app.py not found")
        return

    # Install folder requirements
    install_requirements(folder)

    print(f"[🚀] Starting {folder} on port {port}")
    subprocess.Popen(["python3", app_path, str(port)], cwd=os.path.join(BASE_DIR, folder))

    # Wait until port is open
    for _ in range(60):  # ~30 sec
        if is_port_open(port):
            print(f"[✅] {folder} running on port {port}")
            return
        time.sleep(0.5)
    print(f"[⚠️] {folder} failed to start in time")

# -----------------------------
# Proxy requests
# -----------------------------
def proxy_request(folder):
    port = running_apps.get(folder)
    if not port:
        return Response(f"No running app for '{folder}'", status=404)

    path = request.full_path.replace(f"/{folder}", "")
    if not path.startswith("/"):
        path = "/" + path
    target = f"http://127.0.0.1:{port}{path}"

    try:
        resp = requests.request(
            method=request.method,
            url=target,
            headers={k: v for (k, v) in request.headers if k.lower() != "host"},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30
        )
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded]
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return Response(f"Error forwarding to {folder}: {e}", status=500)

# -----------------------------
# Routes
# -----------------------------
@app.route("/mahi")
def home():
    html = "<h2>🚀 Running API Folders</h2><ul>"
    for f, port in running_apps.items():
        html += f"<li><a href='/{f}/' target='_blank'>{f}</a> (internal port {port})</li>"
    html += "</ul>"
    return html

@app.route("/<folder>/", defaults={'path': ''}, methods=["GET","POST","PUT","DELETE","PATCH"])
@app.route("/<folder>/<path:path>", methods=["GET","POST","PUT","DELETE","PATCH"])
def route_folder(folder, path):
    return proxy_request(folder)

# -----------------------------
# Main
# -----------------------------
def main():
    port = START_PORT
    for folder in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder)
        if os.path.isdir(folder_path) and os.path.exists(os.path.join(folder_path, "app.py")):
            running_apps[folder] = port
            threading.Thread(target=start_app, args=(folder, port), daemon=True).start()
            port += 1

    time.sleep(3)
    print("[✅] All sub-apps initialized:", running_apps)

    main_port = int(os.environ.get("PORT", 8000))
    print(f"[🌐] Main Flask host running on PORT={main_port}")
    app.run(host="0.0.0.0", port=main_port)

if __name__ == "__main__":
    main()
