from flask import Flask, request, jsonify
app = Flask(__name__)

def summarize(docs):
    parts = []
    for d in docs:
        body = d.get("body","")
        first_sent = body.split(".")[0] + ("" if body.endswith(".") else ".")
        parts.append(first_sent.strip())
    return " ".join(parts)

@app.route("/process", methods=["POST"])
def process():
    payload = request.get_json(force=True)
    docs = payload.get("documents", [])
    summary = summarize(docs)
    label = "general"
    text = " ".join([d.get("title","") + " " + d.get("body","") for d in docs]).lower()
    if "security" in text or "auth" in text:
        label = "security"
    elif "idempotency" in text or "idempotent" in text:
        label = "idempotency"
    return jsonify({"summary": summary, "label": label}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
