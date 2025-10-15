# retriever/app.py
from flask import Flask, request, jsonify
import json, os

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "docs.json")

with open(DATA_FILE) as f:
    DOCS = json.load(f)

def score_doc(query, doc):
    qwords = set(query.lower().split())
    text = (doc.get("title","") + " " + doc.get("body","")).lower()
    return sum(1 for w in qwords if w in text)

@app.route("/retrieve", methods=["POST"])
def retrieve():
    payload = request.get_json(force=True)
    query = payload.get("query","")
    scores = [(score_doc(query, d), d) for d in DOCS]
    scores.sort(key=lambda x: x[0], reverse=True)
    top = [d for s,d in scores[:3]]
    return jsonify({"results": top}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
