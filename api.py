from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

DB_FILE = "resumos.json"
WEBHOOK_API_KEY = os.environ.get("WEBHOOK_API_KEY", "")


def load_data():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _autenticar(req):
    """Valida API key no header X-API-Key ou Authorization: Bearer <key>."""
    if not WEBHOOK_API_KEY:
        return True  # sem variável de ambiente configurada, aceita (dev local)
    chave = req.headers.get("X-API-Key") or ""
    bearer = req.headers.get("Authorization", "")
    if bearer.startswith("Bearer "):
        chave = chave or bearer[7:]
    return chave == WEBHOOK_API_KEY


@app.route("/webhook/tldv", methods=["POST"])
def receber_tldv():
    if not _autenticar(request):
        return jsonify({"erro": "Não autorizado"}), 401

    data = request.json
    if not data:
        return jsonify({"erro": "Payload inválido"}), 400

    resumos = load_data()

    novo = {
        "titulo": str(data.get("title", "Sem título")),
        "data": str(data.get("date", "")),
        "resumo": str(data.get("summary", "")),
        "link": str(data.get("url", "")),
        "acoes": data.get("actions", []),
    }

    resumos.insert(0, novo)  # mais recentes primeiro
    save_data(resumos)

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "resumos": len(load_data())}), 200


if __name__ == "__main__":
    app.run(port=5000)
