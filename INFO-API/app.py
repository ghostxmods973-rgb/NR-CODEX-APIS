from flask import Flask
import sys

app = Flask(__name__)

@app.route("/")
def home():
    return f"Hello from {__name__}!"

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(host="127.0.0.1", port=port)
