from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

DB_FILE = "resumos.json"

def load_data():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/webhook/tldv", methods=["POST"])
def receber_tldv():
    data = request.json

    resumos = load_data()

    novo = {
        "titulo": data.get("title"),
        "data": data.get("date"),
        "resumo": data.get("summary"),
        "link": data.get("url"),
        "acoes": data.get("actions", [])
    }

    resumos.append(novo)
    save_data(resumos)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000)
