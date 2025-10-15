# orchestrator/app.py
from flask import Flask, request, jsonify
import requests, json, uuid, time

app = Flask(__name__)

# local service URLs
RETRIEVER_URL = "http://127.0.0.1:5001/retrieve"
PROCESSOR_URL = "http://127.0.0.1:5003/process"
POLICY_URL = "http://127.0.0.1:5004/policy"

# simple in-memory idempotency
IDEMP = {}

@app.route("/process-request", methods=["POST"])
def process_request():
    payload = request.get_json(force=True)
    request_id = payload.get("request_id")
    query = payload.get("query","")
    api_key = request.headers.get("X-API-KEY","-")
    trace_id = str(uuid.uuid4())

    if request_id in IDEMP:
        return jsonify(IDEMP[request_id]), 200

    # Policy check
    p = requests.post(POLICY_URL, json={"query": query})
    if p.status_code != 200:
        return jsonify({"error":"policy denied", "detail": p.json()}), 403

    # Retrieve
    r = requests.post(RETRIEVER_URL, json={"query": query})
    if r.status_code != 200:
        return jsonify({"error":"retriever failed"}), 500
    results = r.json().get("results", [])

    # Process
    proc = requests.post(PROCESSOR_URL, json={"documents": results})
    if proc.status_code != 200:
        return jsonify({"error":"processor failed"}), 500
    proc_json = proc.json()

    response = {
        "request_id": request_id,
        "summary": proc_json.get("summary"),
        "label": proc_json.get("label"),
        "trace_id": trace_id
    }

    IDEMP[request_id] = response
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=True)
