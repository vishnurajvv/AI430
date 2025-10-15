from flask import Flask, request, jsonify
import requests, os, json, uuid, time
from pathlib import Path

app = Flask(__name__)

RETRIEVER_URL = os.getenv("RETRIEVER_URL", "http://retriever:5001/retrieve")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://processor:5003/process")
POLICY_URL = os.getenv("POLICY_URL", "http://policy:5004/policy")

LOG_FILE = Path("/app/logs/audit.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

STORE_FILE = Path("/app/logs/idempotency.json")
if STORE_FILE.exists():
    try:
        IDEMP = json.loads(STORE_FILE.read_text())
    except:
        IDEMP = {}
else:
    IDEMP = {}

def persist_store():
    STORE_FILE.write_text(json.dumps(IDEMP))

def write_log(entry):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

@app.route("/process-request", methods=["POST"])
def process_request():
    payload = request.get_json(force=True)
    request_id = payload.get("request_id")
    query = payload.get("query","")
    api_key = request.headers.get("X-API-KEY","-")
    trace_id = str(uuid.uuid4())

    if request_id in IDEMP:
        entry = {"trace_id": trace_id, "request_id": request_id, "status": "cached", "timestamp": time.time()}
        write_log(entry)
        return jsonify(IDEMP[request_id]), 200

    try:
        # Policy
        p = requests.post(POLICY_URL, json={"query": query}, timeout=5)
        if p.status_code != 200:
            entry = {"trace_id": trace_id, "request_id": request_id, "status": "policy_denied",
                     "policy_resp": p.json(), "timestamp": time.time()}
            write_log(entry)
            return jsonify({"error": "policy denied", "detail": p.json()}), 403

        # Retrieve
        r = requests.post(RETRIEVER_URL, json={"query": query}, timeout=5)
        if r.status_code != 200:
            entry = {"trace_id": trace_id, "request_id": request_id, "status": "retrieve_failed", "timestamp": time.time()}
            write_log(entry)
            return jsonify({"error":"retriever failed"}), 500
        results = r.json().get("results", [])

        # Process
        proc = requests.post(PROCESSOR_URL, json={"documents": results}, timeout=5)
        if proc.status_code != 200:
            entry = {"trace_id": trace_id, "request_id": request_id, "status": "process_failed", "timestamp": time.time()}
            write_log(entry)
            return jsonify({"error":"processor failed"}), 500
        proc_json = proc.json()

        response = {
            "request_id": request_id,
            "summary": proc_json.get("summary"),
            "label": proc_json.get("label"),
            "trace_id": trace_id
        }

        IDEMP[request_id] = response
        persist_store()

        entry = {
            "trace_id": trace_id,
            "request_id": request_id,
            "status": "success",
            "api_key": api_key,
            "query": query,
            "retrieved_ids": [d.get("id") for d in results],
            "label": proc_json.get("label"),
            "timestamp": time.time()
        }
        write_log(entry)
        return jsonify(response), 200

    except Exception as e:
        entry = {"trace_id": trace_id, "request_id": request_id, "status": "error", "error": str(e), "timestamp": time.time()}
        write_log(entry)
        return jsonify({"error": "internal error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
