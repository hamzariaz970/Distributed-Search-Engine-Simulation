# dfs/load_balancers/cluster_manager.py

import os
import sys
import json
import random
import requests
import threading
import time

from flask import Flask, request, jsonify
from flask_cors import CORS

# allow importing dfs.load_balancers.log and DEFAULT_TIMEOUT
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dfs.load_balancers import log, DEFAULT_TIMEOUT

app = Flask(__name__)
CORS(app)  # enable cross-origin so dashboard can fetch /status, /node_heartbeats

# ——— Configuration ———
try:
    NODES = json.loads(os.getenv("NODES", "[]"))
except Exception as e:
    NODES = []
    log(f"Error loading NODES: {e}", context="CLUSTER")

if not NODES:
    log("⚠️ No nodes configured. Set NODES environment variable correctly.", context="CLUSTER")

CHUNK_PENALTY = 50  # MB penalty per stored chunk

# ——— Heartbeat state & monitor ———
NODE_HEARTBEATS = {}  # node_url → { last_seen, status, free_mb, chunk_count }
HEARTBEAT_INTERVAL = 5  # seconds

def node_heartbeat_monitor():
    """
    Periodically ping each node's /status to keep NODE_HEARTBEATS up to date.
    """
    while True:
        for node in NODES:
            try:
                r = requests.get(f"{node}/status", timeout=DEFAULT_TIMEOUT)
                r.raise_for_status()
                data = r.json()
                NODE_HEARTBEATS[node] = {
                    "last_seen":   time.time(),
                    "status":      "alive",
                    "free_mb":     data.get("free_mb", 0),
                    "chunk_count": data.get("chunk_count", 0)
                }
                log(f"Heartbeat OK from {node}", context="HEARTBEAT")
            except Exception as e:
                prev = NODE_HEARTBEATS.get(node, {})
                NODE_HEARTBEATS[node] = {
                    "last_seen":   prev.get("last_seen", 0),
                    "status":      "down",
                    "free_mb":     0,
                    "chunk_count": prev.get("chunk_count", 0)
                }
                log(f"❌ No heartbeat from {node}: {e}", context="HEARTBEAT")
        time.sleep(HEARTBEAT_INTERVAL)

# ——— Node selection logic ———

def get_node_status(node):
    """
    Returns the last-known heartbeat entry for this node,
    or pings it immediately if missing.
    """
    hb = NODE_HEARTBEATS.get(node)
    if hb:
        return {"url": node, **hb}
    # fallback to on-demand ping
    try:
        r = requests.get(f"{node}/status", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return {
            "url":         node,
            "status":      "alive",
            "last_seen":   time.time(),
            "free_mb":     data.get("free_mb", 0),
            "chunk_count": data.get("chunk_count", 0)
        }
    except:
        return None

def compute_score(node_info):
    """
    Score = free_mb - chunk_count * penalty
    """
    return node_info["free_mb"] - (node_info["chunk_count"] * CHUNK_PENALTY)

def select_best_node():
    """
    Chooses an alive node with highest score.
    """
    statuses = []
    for n in NODES:
        info = get_node_status(n)
        if info and info["status"] == "alive":
            try:
                info["score"] = compute_score(info)
                statuses.append(info)
            except Exception as e:
                log(f"Error computing score for {n}: {e}", context="CLUSTER")

    if not statuses:
        log("No available alive nodes", context="CLUSTER")
        return None

    max_score = max(s["score"] for s in statuses)
    top = [s for s in statuses if abs(s["score"] - max_score) < 1e-3]
    chosen = random.choice(top)
    log(f"[SELECTED NODE] {chosen['url']} → Score: {chosen['score']}", context="CLUSTER")
    return chosen["url"]

# ——— HTTP Endpoints ———

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk    = request.files.get("chunk")
    chunk_id = request.form.get("chunk_id")
    if not chunk or not chunk_id:
        log("Missing chunk or chunk_id", context="CLUSTER")
        return jsonify({"error": "Missing chunk or chunk_id"}), 400

    node = select_best_node()
    if not node:
        return jsonify({"error": "No available nodes"}), 503

    try:
        r = requests.post(
            f"{node}/store",
            files={"chunk": (chunk.filename, chunk.stream, chunk.mimetype)},
            data={"chunk_id": chunk_id},
            timeout=DEFAULT_TIMEOUT
        )
        r.raise_for_status()
        log(f"Forwarded {chunk_id} to {node}", context="CLUSTER")
        return jsonify({"status": "stored", "node": node, "chunk_id": chunk_id}), 200
    except Exception as e:
        log(f"Upload to node {node} failed: {e}", context="CLUSTER")
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def cluster_status():
    """
    Returns aggregate cluster info plus a summary of node heartbeats.
    """
    total_free   = 0
    total_chunks = 0
    active_nodes = 0

    for node, hb in NODE_HEARTBEATS.items():
        total_free   += hb.get("free_mb", 0)
        total_chunks += hb.get("chunk_count", 0)
        if hb.get("status") == "alive":
            active_nodes += 1

    return jsonify({
        "cluster_free_mb":    total_free,
        "cluster_chunk_count": total_chunks,
        "active_nodes":        active_nodes,
        "node_heartbeats":     NODE_HEARTBEATS
    }), 200

@app.route('/node_heartbeats', methods=['GET'])
def node_heartbeats():
    """
    Returns detailed per-node heartbeat info.
    """
    return jsonify(NODE_HEARTBEATS), 200

@app.route('/', methods=['GET'])
def index():
    return "Cluster Manager is running", 200

# ——— Launcher ———

if __name__ == '__main__':
    # start the background monitor thread
    threading.Thread(target=node_heartbeat_monitor, daemon=True).start()

    import argparse
    parser = argparse.ArgumentParser(description="DFS Cluster Manager")
    parser.add_argument('--port', type=int, default=7001)
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port, debug=True)
