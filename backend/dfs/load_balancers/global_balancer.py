# dfs/load_balancers/global_balancer.py

import os
import sys
import json
import threading
import time
import requests

from flask import Flask, request, jsonify, abort
from flask_cors import CORS

# make sure we can import our shared log/timeout helpers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dfs.load_balancers import log, DEFAULT_TIMEOUT

app = Flask(__name__)
CORS(app)  # allow cross-origin requests from your front-end

# —— Configuration —— 
try:
    CLUSTERS = json.loads(os.getenv("CLUSTERS", "{}"))
except Exception as e:
    CLUSTERS = {}
    log(f"Failed to parse CLUSTERS env var: {e}", context="GLOBAL")

if not CLUSTERS:
    log("⚠️ No clusters configured. Set CLUSTERS environment variable correctly.", context="GLOBAL")
else:
    log(f"Clusters configured: {list(CLUSTERS.keys())}", context="GLOBAL")

# —— Heartbeat state —— 
CLUSTER_HEARTBEATS = {}        # { cluster_name: {last_seen, free_mb, status} }
HEARTBEAT_INTERVAL = 30        # seconds (was 10)

def get_cluster_status(url):
    """
    Ping a cluster manager's /status endpoint.
    """
    try:
        r = requests.get(f"{url}/status", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        name = next((n for n,v in CLUSTERS.items() if v == url), url)
        return {
            "url": url,
            "name": name,
            "free_mb": data.get("cluster_free_mb", 0)
        }
    except Exception as e:
        log(f"Cluster {url} unreachable: {e}", context="GLOBAL")
        return None

def heartbeat_monitor():
    """
    Background thread: periodically refresh CLUSTER_HEARTBEATS.
    """
    while True:
        for name, url in CLUSTERS.items():
            status = get_cluster_status(url)
            if status:
                CLUSTER_HEARTBEATS[name] = {
                    "last_seen": time.time(),
                    "free_mb":   status["free_mb"],
                    "status":    "alive"
                }
                log(f"Heartbeat OK from {name}", context="HEARTBEAT")
            else:
                prev = CLUSTER_HEARTBEATS.get(name, {})
                CLUSTER_HEARTBEATS[name] = {
                    "last_seen": prev.get("last_seen", 0),
                    "free_mb":   0,
                    "status":    "down"
                }
                log(f"❌ No heartbeat from {name}", context="HEARTBEAT")
        time.sleep(HEARTBEAT_INTERVAL)

# —— API Endpoints —— 

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    """
    Receives a chunk and forwards it to the best cluster manager.
    """
    chunk = request.files.get("chunk")
    chunk_id = request.form.get("chunk_id")
    if not chunk or not chunk_id:
        return jsonify({"error": "Missing chunk or chunk_id"}), 400

    alive = [n for n,v in CLUSTER_HEARTBEATS.items() if v["status"] == "alive"]
    if not alive:
        return jsonify({"error": "No available clusters"}), 503

    best       = max(alive, key=lambda n: CLUSTER_HEARTBEATS[n]["free_mb"])
    target_url = CLUSTERS[best]

    try:
        r = requests.post(
            f"{target_url}/upload_chunk",
            files={"chunk": (chunk.filename, chunk.stream, chunk.mimetype)},
            data={"chunk_id": chunk_id},
            timeout=DEFAULT_TIMEOUT
        )
        r.raise_for_status()
        resp = r.json()
        log(f"Forwarded {chunk_id} to {best}", context="GLOBAL")
        return jsonify({
            "status":  "stored",
            "cluster": best,
            "node":    resp.get("node", "unknown"),
            "chunk_id": chunk_id
        }), 200
    except Exception as e:
        log(f"Upload to cluster {best} failed: {e}", context="GLOBAL")
        return jsonify({"error": str(e)}), 500

@app.route('/heartbeats', methods=['GET'])
def heartbeats():
    """
    Expose the latest heartbeat info for all clusters,
    *including* their URLs so the front-end can fetch node heartbeats.
    """
    out = {}
    for name, info in CLUSTER_HEARTBEATS.items():
        out[name] = {
            "url":      CLUSTERS.get(name),
            "status":   info["status"],
            "free_mb":  info["free_mb"],
            "last_seen": info["last_seen"]
        }
    return jsonify(out), 200


@app.route('/', methods=['GET'])
def index():
    return "🌍 Global Load Balancer is running", 200

if __name__ == '__main__':
    # start our heartbeat monitor thread
    threading.Thread(target=heartbeat_monitor, daemon=True).start()

    import argparse
    parser = argparse.ArgumentParser(description="Global Load Balancer")
    parser.add_argument('--port', type=int, default=6001)
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port, debug=True)
