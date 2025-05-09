# start_clusters.py
import os
import subprocess
import time
import json
import sys
import threading
import requests

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def start_process(cmd, cwd=None, env=None):
    try:
        env = env or os.environ.copy()
        env["PYTHONPATH"] = BASE_DIR
        return subprocess.Popen(cmd, cwd=cwd or BASE_DIR, env=env)
    except Exception as e:
        print(f"[ERROR] Failed to start process: {' '.join(cmd)} — {e}")
        return None

def get_free_ports(start, count):
    return [start + i for i in range(count)]

def launch_nodes(cluster_id, node_ports):
    procs = []
    for port in node_ports:
        print(f"Starting storage node on port {port}...")
        p = start_process(["python", "dfs/nodes/node_storage.py", "--port", str(port)])
        if p: procs.append(p)
        else: print(f"[WARN] Node on port {port} did not start.")
    return procs

def launch_cluster_manager(cluster_port, node_ports):
    node_urls = json.dumps([f"http://localhost:{p}" for p in node_ports])
    env = os.environ.copy()
    env["NODES"] = node_urls
    env["PYTHONPATH"] = BASE_DIR
    print(f"Starting cluster manager on port {cluster_port}...")
    return start_process(
        ["python", "dfs/load_balancers/cluster_manager.py", "--port", str(cluster_port)],
        env=env
    )

def launch_global_balancer(cluster_map):
    env = os.environ.copy()
    env["CLUSTERS"] = json.dumps(cluster_map)
    env["PYTHONPATH"] = BASE_DIR
    print("Starting global load balancer on port 6000...")
    
    return start_process(["python", "dfs/load_balancers/global_balancer.py", "--port", "6001"], env=env)

def monitor_heartbeats(cluster_map, interval=10):
    """
    Periodically polls the global balancer and each cluster manager for status.
    """
    gb_url = "http://localhost:6000/heartbeats"
    while True:
        print("\n--- HEARTBEAT CHECK ---")
        # 1) Global Balancer heartbeats
        try:
            resp = requests.get(gb_url, timeout=5)
            data = resp.json()
            print(f"[GLOBAL] heartbeats:", json.dumps(data, indent=2))
        except Exception as e:
            print(f"[ERROR] Global balancer heartbeat failed: {e}")

        # 2) Each cluster manager status
        for name, url in cluster_map.items():
            status_url = f"{url}/status"
            try:
                resp = requests.get(status_url, timeout=5)
                data = resp.json()
                print(f"[{name}] status:", json.dumps(data, indent=2))
            except Exception as e:
                print(f"[ERROR] {name} status check failed: {e}")

        print("--- end heartbeat ---\n")
        time.sleep(interval)

def start_clusters_and_nodes():
    print("Starting clusters and nodes...")
    try:
        clusters = int(input("How many clusters? ").strip())
        nodes_per_cluster = int(input("Nodes per cluster? ").strip())
    except ValueError:
        print("[ERROR] Invalid numbers.")
        return

    node_base_port = 5001
    cluster_base_port = 7001

    all_node_procs = []
    cluster_mgr_procs = []
    cluster_map = {}

    # 1) Launch clusters
    for c in range(clusters):
        node_ports = get_free_ports(node_base_port + c*nodes_per_cluster, nodes_per_cluster)
        cluster_port = cluster_base_port + c

        cm = launch_cluster_manager(cluster_port, node_ports)
        if cm: cluster_mgr_procs.append(cm)

        nodes = launch_nodes(c, node_ports)
        all_node_procs.extend(nodes)

        cluster_map[f"cluster_{c+1}"] = f"http://localhost:{cluster_port}"
        time.sleep(1)

    # 2) Launch global balancer
    gb = launch_global_balancer(cluster_map)
    time.sleep(1)

    # 3) Start heartbeat monitor thread
    monitor_thread = threading.Thread(
        target=monitor_heartbeats,
        args=(cluster_map, 10),
        daemon=True
    )
    monitor_thread.start()

    print("\n✅ System is live! Press Ctrl+C to shut down.\n")

    try:
        while True:
            time.sleep(60)  # just keep main thread alive
    except KeyboardInterrupt:
        print("\nShutting down all processes...")
    finally:
        for p in all_node_procs + cluster_mgr_procs + ([gb] if gb else []):
            if p:
                print(f"Terminating PID {p.pid}...")
                p.terminate()

if __name__ == "__main__":
    start_clusters_and_nodes()
