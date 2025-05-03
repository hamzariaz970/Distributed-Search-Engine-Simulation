from flask import Flask, request, jsonify
import os
import requests
import json
from dfs.load_balancers import log, DEFAULT_TIMEOUT

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


app = Flask("global_balancer")

# Load clusters from environment
CLUSTERS = json.loads(os.getenv("CLUSTERS", "{}"))

if not CLUSTERS:
    log("⚠️ No clusters configured. Set CLUSTERS environment variable correctly.", context="GLOBAL")

log(f"Clusters configured: {list(CLUSTERS.keys())}", context="GLOBAL")

def get_cluster_status(url):
    try:
        r = requests.get(f"{url}/status", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return {
            "url": url,
            "free_mb": r.json().get("cluster_free_mb", 0),
            "name": [k for k, v in CLUSTERS.items() if v == url][0]
        }
    except Exception as e:
        log(f"Cluster {url} unreachable: {e}", context="GLOBAL")
        return None

def select_cluster():
    statuses = [get_cluster_status(url) for url in CLUSTERS.values()]
    statuses = [s for s in statuses if s]
    if statuses:
        best = max(statuses, key=lambda x: x["free_mb"])
        log(f"Cluster selected: {best['name']} with {best['free_mb']} MB free", context="GLOBAL")
        return best
    return None

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk = request.files.get("chunk")
    chunk_id = request.form.get("chunk_id")

    if not chunk or not chunk_id:
        return jsonify({"error": "Missing chunk or chunk_id"}), 400

    cluster = select_cluster()
    if not cluster:
        log("No active clusters available", context="GLOBAL")
        return jsonify({"error": "No available clusters"}), 503

    try:
        r = requests.post(
            f"{cluster['url']}/upload_chunk",
            files={"chunk": (chunk.filename, chunk.stream, chunk.mimetype)},
            data={"chunk_id": chunk_id},
            timeout=DEFAULT_TIMEOUT
        )
        r.raise_for_status()
        response_data = r.json()
        log(f"Forwarded {chunk_id} to {cluster['name']}", context="GLOBAL")
        return jsonify({
            "status": "stored",
            "cluster": cluster['name'],
            "node": response_data["node"],
            "chunk_id": chunk_id
        }), 200
    except requests.exceptions.RequestException as e:
        log(f"Upload to cluster {cluster['name']} failed: {e}", context="GLOBAL")
        return jsonify({"error": f"Upload failed to cluster {cluster['name']}", "details": str(e)}), 500

@app.route('/')
def index():
    return "🌍 Global Load Balancer is running", 200

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=6000)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)
