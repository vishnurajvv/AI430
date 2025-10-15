# policy/app.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/policy", methods=["POST"])
def policy():
    payload = request.get_json(force=True)
    query = payload.get("query","")
    if "forbidden" in query.lower():
        return jsonify({"allowed": False, "reason": "Query contains forbidden term"}), 403
    return jsonify({"allowed": True}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5004, debug=True)
