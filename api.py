from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

DB_FILE = "resumos.json"

REQUIRED_FIELDS = ["title", "date", "summary"]


def load_data():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route("/webhook/tldv", methods=["POST"])
def receber_tldv():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON inválido ou ausente"}), 400

    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return jsonify({"error": f"Campos obrigatórios faltando: {missing}"}), 400

    novo = {
        "titulo": data["title"],
        "data": data["date"],
        "resumo": data["summary"],
        "link": data.get("url", ""),
        "acoes": data.get("actions", []),
    }

    resumos = load_data()
    resumos.append(novo)
    save_data(resumos)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000)
