import os
import json
import random
import requests
from flask import Flask, request, jsonify
from dfs.load_balancers import log, DEFAULT_TIMEOUT

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


app = Flask("cluster_manager")

# Dynamically load node list from environment variable
NODES = json.loads(os.getenv("NODES", "[]"))

if not NODES:
    log("⚠️ No nodes configured. Set NODES environment variable correctly.", context="CLUSTER")

CHUNK_PENALTY = 50  # MB penalty per stored chunk

def get_node_status(node):
    try:
        r = requests.get(f"{node}/status", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return {
            "url": node,
            "free_mb": r.json().get("free_mb", 0),
            "chunk_count": r.json().get("chunk_count", 9999)
        }
    except Exception as e:
        log(f"Node {node} unreachable: {e}", context="CLUSTER")
        return None

def compute_score(node):
    return node["free_mb"] - (node["chunk_count"] * CHUNK_PENALTY)

def select_best_node():
    statuses = [get_node_status(n) for n in NODES]
    statuses = [s for s in statuses if s]

    if not statuses:
        return None

    for node in statuses:
        node["score"] = compute_score(node)

    max_score = max(n["score"] for n in statuses)
    top_nodes = [n for n in statuses if abs(n["score"] - max_score) < 1e-3]

    best = random.choice(top_nodes)

    log(
        f"[SELECTED NODE] {best['url']} → Score: {best['score']} | Free: {best['free_mb']} MB | Chunks: {best['chunk_count']}",
        context="CLUSTER"
    )

    return best["url"]

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk = request.files.get("chunk")
    chunk_id = request.form.get("chunk_id")

    if not chunk or not chunk_id:
        log("Missing chunk or chunk_id", context="CLUSTER")
        return jsonify({"error": "Missing chunk or chunk_id"}), 400

    node = select_best_node()
    if not node:
        log("No available nodes to handle request", context="CLUSTER")
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
        return jsonify({"error": f"Failed to upload to {node}", "details": str(e)}), 500

@app.route('/status', methods=['GET'])
def cluster_status():
    total_free = 0
    total_chunks = 0
    active_nodes = 0

    for node in NODES:
        status = get_node_status(node)
        if status:
            total_free += status["free_mb"]
            total_chunks += status["chunk_count"]
            active_nodes += 1

    return jsonify({
        "cluster_free_mb": total_free,
        "cluster_chunk_count": total_chunks,
        "active_nodes": active_nodes
    })

@app.route('/')
def index():
    return "Cluster Manager is running", 200

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=7001)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)
